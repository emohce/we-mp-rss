from __future__ import annotations

import json
from typing import Callable
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from core.models.feed import Feed

from .collector import CollectedPage, CollectorError


TokenGetter = Callable[[str, str], str]


def _runtime_token_getter(key: str, default: str = "") -> str:
    # Import lazily: the legacy token module owns its local credential file.
    from driver.token import get

    return get(key, default)


def _bounded_json(response: requests.Response, *, max_bytes: int = 5 * 1024 * 1024) -> dict:
    content_length = int(response.headers.get("content-length") or 0)
    if content_length > max_bytes or len(response.content) > max_bytes:
        raise CollectorError("response_too_large", safe_message="provider response exceeded 5 MiB")
    try:
        value = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise CollectorError("invalid_json", safe_message="provider returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise CollectorError("invalid_payload", safe_message="provider returned an invalid payload")
    return value


class WeMpRssCollectorAdapter:
    """Single-request adapter for the existing authenticated WeChat backend session.

    It deliberately does not sleep, retry, follow redirects, fetch article bodies
    or advance more than one page. The durable worker owns those decisions.
    """

    endpoint = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        token_getter: TokenGetter = _runtime_token_getter,
        http: requests.Session | None = None,
    ):
        self.session_factory = session_factory
        self.token_getter = token_getter
        self.http = http or requests.Session()

    def fetch_page(
        self,
        *,
        source_id: str,
        cursor: dict,
        page_budget: int,
    ) -> CollectedPage:
        if page_budget != 1:
            raise CollectorError("page_budget", safe_message="we-mp-rss adapter allows one page")
        with self.session_factory() as session:
            feed = session.get(Feed, source_id)
            if feed is None or not feed.faker_id:
                raise CollectorError("source_not_found", safe_message="公众号来源尚未完成标识解析")
            faker_id = str(feed.faker_id)

        token = self.token_getter("token", "")
        cookie = self.token_getter("cookie", "")
        if not token or not cookie:
            raise CollectorError("200003", safe_message="公众号后台授权不存在或已失效")
        page = max(0, int(cursor.get("page", 0)))
        count = 5
        try:
            response = self.http.get(
                self.endpoint,
                params={
                    "sub": "list",
                    "sub_action": "list_ex",
                    "begin": page * count,
                    "count": count,
                    "fakeid": faker_id,
                    "token": token,
                    "lang": "zh_CN",
                    "f": "json",
                    "ajax": 1,
                },
                headers={
                    "Cookie": cookie,
                    "User-Agent": "Mozilla/5.0 WeRSS/2.0",
                    "Accept": "application/json,text/plain,*/*",
                },
                timeout=(10, 30),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise CollectorError("network_error", safe_message="公众号后台请求失败") from exc
        if response.status_code == 429:
            raise CollectorError(
                "200013",
                http_status=429,
                retry_after_seconds=_retry_after(response),
                safe_message="公众号后台触发频率控制",
            )
        if response.status_code in {301, 302, 303, 307, 308, 401, 403}:
            raise CollectorError("200003", http_status=401, safe_message="公众号后台授权已失效")
        if response.status_code >= 500:
            raise CollectorError(
                f"http_{response.status_code}",
                http_status=response.status_code,
                safe_message="公众号后台暂时不可用",
            )
        payload = _bounded_json(response)
        base_response = payload.get("base_resp") or {}
        provider_code = str(base_response.get("ret", ""))
        if provider_code and provider_code != "0":
            raise CollectorError(
                provider_code,
                retry_after_seconds=_retry_after(response),
                safe_message=(
                    "公众号后台触发频率控制"
                    if provider_code == "200013"
                    else "公众号后台返回受控错误"
                ),
            )

        publish_page = payload.get("publish_page")
        if isinstance(publish_page, str):
            try:
                publish_page = json.loads(publish_page)
            except json.JSONDecodeError as exc:
                raise CollectorError(
                    "invalid_publish_page",
                    safe_message="公众号文章页数据无法解析",
                ) from exc
        publish_page = publish_page if isinstance(publish_page, dict) else {}
        articles: list[dict] = []
        for published in publish_page.get("publish_list") or []:
            if not isinstance(published, dict):
                continue
            raw_info = published.get("publish_info") or {}
            if isinstance(raw_info, str):
                try:
                    raw_info = json.loads(raw_info)
                except json.JSONDecodeError:
                    continue
            if not isinstance(raw_info, dict):
                continue
            for item in raw_info.get("appmsgex") or []:
                normalized = _normalize_wechat_article(source_id, item, raw_info)
                if normalized:
                    articles.append(normalized)
        return CollectedPage(
            articles=tuple(articles),
            next_cursor={"page": page + 1, "exhausted": not bool(articles)},
            ingestion_source="we-mp-rss",
        )


class PaidJsonApiCollectorAdapter:
    """Allowlisted HTTPS adapter for a paid/recharged aggregation API contract."""

    def __init__(
        self,
        *,
        endpoint: str,
        allowed_hosts: set[str],
        api_key_getter: Callable[[], str],
        http: requests.Session | None = None,
    ):
        parsed = urlparse(endpoint)
        normalized_hosts = {host.lower() for host in allowed_hosts}
        if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.lower() not in normalized_hosts:
            raise ValueError("paid API endpoint must be HTTPS and host-allowlisted")
        self.endpoint = endpoint
        self.api_key_getter = api_key_getter
        self.http = http or requests.Session()

    def fetch_page(
        self,
        *,
        source_id: str,
        cursor: dict,
        page_budget: int,
    ) -> CollectedPage:
        if page_budget != 1:
            raise CollectorError("page_budget", safe_message="paid API adapter allows one page")
        api_key = self.api_key_getter()
        if not api_key:
            raise CollectorError("auth_invalid", safe_message="付费 API 密钥尚未配置")
        try:
            response = self.http.get(
                self.endpoint,
                params={"source_id": source_id, "cursor": json.dumps(cursor, separators=(",", ":"))},
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                timeout=(10, 30),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise CollectorError("network_error", safe_message="付费 API 请求失败") from exc
        if response.status_code == 429:
            raise CollectorError(
                "rate_limited",
                http_status=429,
                retry_after_seconds=_retry_after(response),
                safe_message="付费 API 额度或频率受限",
            )
        if response.status_code in {301, 302, 303, 307, 308, 401, 403}:
            raise CollectorError("auth_invalid", http_status=401, safe_message="付费 API 授权失败")
        if response.status_code >= 400:
            raise CollectorError(
                f"http_{response.status_code}",
                http_status=response.status_code,
                safe_message="付费 API 返回错误",
            )
        payload = _bounded_json(response)
        raw_articles = payload.get("articles") or []
        if not isinstance(raw_articles, list) or not isinstance(payload.get("next_cursor", {}), dict):
            raise CollectorError("invalid_payload", safe_message="付费 API 响应不符合适配契约")
        articles = []
        for item in raw_articles:
            if isinstance(item, dict):
                normalized = dict(item)
                normalized.setdefault("mp_id", source_id)
                articles.append(normalized)
        return CollectedPage(
            articles=tuple(articles),
            next_cursor=payload.get("next_cursor") or {},
            ingestion_source="paid-api",
        )


def _normalize_wechat_article(source_id: str, item: object, publish_info: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    raw_id = str(item.get("aid") or item.get("id") or "").strip()
    if not raw_id:
        return None
    canonical_id = f"{source_id}-{raw_id}".replace("MP_WXS_", "")
    return {
        "id": canonical_id[:255],
        "mp_id": source_id,
        "title": item.get("title"),
        "pic_url": item.get("cover") or item.get("cover_img") or item.get("pic_url"),
        "url": item.get("link") or item.get("url"),
        "description": item.get("digest") or item.get("description"),
        "publish_time": item.get("update_time") or item.get("publish_time") or item.get("create_time"),
        "create_time": item.get("create_time"),
        "publish_info": json.dumps(publish_info, ensure_ascii=False, separators=(",", ":")),
        "status": 1,
    }


def _retry_after(response: requests.Response) -> int | None:
    try:
        value = int(response.headers.get("retry-after") or 0)
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None
