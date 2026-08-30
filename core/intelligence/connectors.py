"""Capability registry and bounded, offline-only inbound contracts.

No URL fetch, subprocess, OAuth, subscription write or paid fallback lives here.
Supplier verification and local format verification are deliberately separate.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import ipaddress
import json
from pathlib import PurePath
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from sqlalchemy import func, select, update
from bs4 import BeautifulSoup
from core.models.article import Article
from .daily import queue_reconciliations
from .models import (ConnectorIdentity, ConnectorUsage, OutboxEvent, Workspace,
                     WorkspaceArticle, WorkflowJob, utcnow)
from .search import index_article

MAX_BYTES = 1024 * 1024
MAX_ITEMS = 100
REGISTRY = (
    {"provider": "we-mp-rss", "label": "we-mp-rss 核心", "supplier_state": "adapter-ready",
     "offline_contract": "single-page-tests", "capabilities": ["head", "backfill"],
     "runtime_policy": "explicit_collector_flag", "limits": "账号/来源预算；不自动补抓正文"},
    {"provider": "local-feed", "label": "本地 Feed 文件", "supplier_state": "not-applicable",
     "offline_contract": "format-fixtures", "capabilities": ["rss", "atom", "json-feed", "opml-preview"],
     "runtime_policy": "local_file_only", "limits": "1 MiB / 100 篇；OPML 仅预览，不订阅或抓取"},
    {"provider": "supsub", "label": "SupSub", "supplier_state": "researched",
     "offline_contract": "generic-feed-and-cli-envelope-fixtures", "capabilities": ["feed-file", "cli-read-plan"],
     "runtime_policy": "disabled", "limits": "无真实字段/账号验收；禁止精读、分享、已读与订阅写入"},
    {"provider": "wechat2rss", "label": "Wechat2RSS 参照", "supplier_state": "disabled",
     "offline_contract": "feed-preview-only", "capabilities": ["feed-preview"],
     "runtime_policy": "disabled", "limits": "许可/分发门禁；最新 20 篇，不作历史补采"},
    {"provider": "paid-api", "label": "通用充值 API", "supplier_state": "adapter-ready",
     "offline_contract": "generic-http-fixtures", "capabilities": ["json-page"],
     "runtime_policy": "disabled", "limits": "未绑定供应商；默认禁止计费，单位预算不等于货币报价"},
)


def capabilities():
    return [{**item, "capabilities": list(item["capabilities"]), "connection_status": "unverified",
             "automatic_fallback": False, "last_public_review": "2026-08-30"} for item in REGISTRY]


def _digest(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _text(value, limit, name):
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise ValueError(f"invalid {name}")
    return value.strip()


def canonical_url(value):
    value = _text(value, 500, "article URL")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("article URL must be public HTTP(S), without embedded credentials")
        hostname = parsed.hostname.lower()
        if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
            raise ValueError("private article URL is not allowed")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("private article URL is not allowed")
        query = parse_qsl(parsed.query, keep_blank_values=True)
        if any(key.lower().replace("-", "_") in {"k", "key", "token", "access_token", "api_key", "secret", "auth", "signature"} for key, _ in query):
            raise ValueError("credential-bearing URL requires separate secret storage")
        query = [(key, item) for key, item in query if not key.lower().startswith("utm_")]
        netloc = f"[{hostname}]" if ":" in hostname else hostname
        if parsed.port and (parsed.scheme, parsed.port) not in {("http", 80), ("https", 443)}:
            netloc += f":{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path or "/", urlencode(query), ""))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("unsafe or invalid article URL; remove secrets before import") from exc


def _timestamp(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("publication time must be a string with timezone")
    try:
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            parsed = parsedate_to_datetime(value.strip())
        if parsed.tzinfo is None:
            raise ValueError("publication time must include a timezone")
        timestamp = int(parsed.timestamp())
        if timestamp < 0 or timestamp > 2147483647:
            raise ValueError("publication time out of range")
        return timestamp
    except (TypeError, OverflowError, ValueError) as exc:
        raise ValueError("invalid or timezone-ambiguous publication date") from exc


def sanitize_import_html(value):
    """Keep readable structural HTML safe for the shared legacy renderer too."""
    soup = BeautifulSoup(value, "html.parser")
    blocked = {"script", "style", "meta", "base", "link", "iframe", "object", "embed", "form", "input", "button",
               "textarea", "select", "video", "audio", "source", "svg", "math", "template"}
    allowed = {"p", "br", "div", "span", "article", "section", "main", "h1", "h2", "h3", "h4", "h5", "h6",
               "ul", "ol", "li", "blockquote", "pre", "code", "strong", "em", "b", "i", "u", "s", "table",
               "thead", "tbody", "tfoot", "tr", "th", "td", "hr", "a", "img", "figure", "figcaption", "dl", "dt", "dd"}
    for tag in list(soup.find_all(True)):
        if not tag.name:
            continue
        if tag.name in blocked:
            tag.decompose(); continue
        if tag.name not in allowed:
            tag.unwrap(); continue
        clean = {}
        for name, attribute in tag.attrs.items():
            if name in {"alt", "title"} and isinstance(attribute, str):
                clean[name] = attribute[:1000]
            elif name in {"colspan", "rowspan", "width", "height"} and re.fullmatch(r"[0-9]{1,3}", str(attribute)):
                clean[name] = str(attribute)
            elif tag.name == "a" and name == "href":
                try:
                    clean["href"] = canonical_url(attribute)
                    clean["rel"] = "noopener noreferrer"
                except ValueError:
                    pass
            elif tag.name == "img" and name == "src" and isinstance(attribute, str) and re.match(r"^data:image/(png|jpeg|gif|webp);base64,", attribute, re.I):
                clean["src"] = attribute
        tag.attrs = clean
        if tag.name == "img" and "src" not in clean:
            tag.replace_with(clean.get("alt", "[远程图片未导入]"))
    return str(soup)


@dataclass(frozen=True)
class FeedEntry:
    external_id: str
    title: str
    url: str
    description: str
    body: str
    published_at: int | None


def _entry(external_id, title, url, description, body, published):
    canonical = canonical_url(url) if url else ""
    external_id = _text(str(external_id or canonical), 255, "external identity")
    if external_id.startswith(("http://", "https://")):
        external_id = canonical_url(external_id)
    if not external_id:
        raise ValueError("entry needs a stable external ID or canonical article URL")
    return FeedEntry(external_id, _text(title or "", 1000, "title"), canonical,
                     BeautifulSoup(sanitize_import_html(_text(description or "", 20000, "description")), "html.parser").get_text(" ", strip=True),
                     sanitize_import_html(_text(body or "", MAX_BYTES, "body")),
                     _timestamp(published))


def parse_feed(content):
    """Parse one window, never infer historical completeness from an empty feed."""
    if not isinstance(content, str) or len(content.encode()) > MAX_BYTES or "\x00" in content:
        raise ValueError("feed must be UTF-8 text within 1 MiB")
    stripped = content.lstrip("\ufeff \r\n\t")
    if stripped.startswith("{"):
        try:
            value = json.loads(stripped)
        except (ValueError, RecursionError) as exc:
            raise ValueError("invalid JSON Feed") from exc
        if not isinstance(value, dict) or value.get("version") not in {"https://jsonfeed.org/version/1", "https://jsonfeed.org/version/1.1"} or not isinstance(value.get("items"), list):
            raise ValueError("expected JSON Feed 1 or 1.1 items")
        if len(value["items"]) > MAX_ITEMS:
            raise ValueError("feed window exceeds 100 items; split explicitly")
        entries = []
        for item in value["items"]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("JSON Feed item requires a string ID")
            body = item.get("content_html") or ("<p>" + html.escape(item["content_text"]) + "</p>" if isinstance(item.get("content_text"), str) else "")
            entries.append(_entry(item["id"], item.get("title"), item.get("url"), item.get("summary"), body,
                                  item.get("date_published") or ""))
        return "json-feed", tuple(entries)
    root = _xml(stripped)
    if root.tag == "opml":
        return "opml", tuple(_opml(root))
    if root.tag == "rss":
        channel = root.find("channel")
        if channel is None:
            raise ValueError("RSS channel missing")
        items, kind = channel.findall("item"), "rss"
        entries = [_entry(item.findtext("guid"), item.findtext("title"), item.findtext("link"), item.findtext("description"),
                          item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or item.findtext("description"),
                          item.findtext("pubDate") or "") for item in _bounded_items(items)]
    elif root.tag == "{http://www.w3.org/2005/Atom}feed":
        ns = "{http://www.w3.org/2005/Atom}"
        items, kind = root.findall(ns + "entry"), "atom"
        entries = []
        for item in _bounded_items(items):
            link = next((link.get("href") for link in item.findall(ns + "link") if link.get("rel", "alternate") == "alternate"), "")
            content_node = item.find(ns + "content")
            body = ""
            if content_node is not None:
                if content_node.get("src"):
                    raise ValueError("external Atom content is not fetched")
                body = content_node.text or ""
                if content_node.get("type", "text") == "text":
                    body = "<p>" + html.escape(body) + "</p>"
                elif content_node.get("type") != "html":
                    raise ValueError("Atom XHTML requires a separately verified converter")
            entries.append(_entry(item.findtext(ns + "id"), item.findtext(ns + "title"), link,
                                  item.findtext(ns + "summary"), body,
                                  item.findtext(ns + "published") or item.findtext(ns + "updated") or ""))
    else:
        raise ValueError("only RSS 2, Atom 1, JSON Feed and OPML preview are supported")
    return kind, tuple(entries)


def _bounded_items(items):
    if len(items) > MAX_ITEMS:
        raise ValueError("feed window exceeds 100 items; split explicitly")
    return items


def _xml(content):
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", content, re.I):
        raise ValueError("XML DTD and entities are forbidden")
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError) as exc:
        raise ValueError("invalid XML feed") from exc
    stack, nodes = [(root, 0)], 0
    while stack:
        node, depth = stack.pop(); nodes += 1
        if nodes > 5000 or depth > 24:
            raise ValueError("XML structural limit exceeded")
        stack.extend((child, depth + 1) for child in node)
    return root


def _opml(root):
    proposals = []
    def visit(node, groups):
        for child in node:
            label = _text(child.get("text") or child.get("title") or "", 255, "OPML title")
            if child.tag == "outline" and child.get("xmlUrl"):
                raw = child.get("xmlUrl")
                try:
                    url = canonical_url(raw)
                    # Query-bearing feed addresses can be capability URLs even
                    # without a recognizable token key. Never echo them.
                    if urlsplit(url).query:
                        raise ValueError("possible secret")
                except ValueError:
                    url = ""
                proposals.append({"identity": _digest(raw), "name": label, "groups": list(groups),
                                  "public_url": url, "requires_secret_ref": not bool(url)})
            else:
                visit(child, groups + ([label] if child.tag == "outline" and label else []))
    visit(root, [])
    unique = {proposal["identity"]: proposal for proposal in proposals}
    return _bounded_items(list(unique.values()))


def preview_feed(content, provider="local-feed"):
    if provider not in {"local-feed", "supsub", "wechat2rss"}:
        raise ValueError("unsupported file provider")
    kind, entries = parse_feed(content)
    if kind == "opml":
        return {"format": kind, "entries": entries, "count": len(entries), "can_import": False,
                "warning": "仅预览来源与分组；不保存带密钥 URL，不自动订阅或请求网络"}
    return {"format": kind, "count": len(entries), "can_import": provider != "wechat2rss",
            "entries": [{"external_id": row.external_id, "title": row.title, "url": row.url,
                         "published_at": row.published_at, "has_body": bool(row.body)} for row in entries],
            "warning": "只代表文件窗口，不证明历史完整；缺少日期的条目不会自动进入日期日报"}


@dataclass(frozen=True)
class UsagePolicy:
    daily_units: int = 500
    allow_billable: bool = False


def reserve_usage(session, *, workspace_id, provider, operation, request_id, fingerprint,
                  units=1, billable=False, policy=UsagePolicy(), now=None):
    """The caller owns the transaction. Unknown/reserved spend is never refunded."""
    now = now or utcnow()
    if provider not in {item["provider"] for item in REGISTRY} or operation not in {"file-import", "read-plan", "paid-page"}:
        raise ValueError("unsupported metered operation")
    if not isinstance(request_id, str) or not 8 <= len(request_id) <= 120 or type(units) is not int or not 1 <= units <= MAX_ITEMS:
        raise ValueError("invalid usage request")
    if type(policy.daily_units) is not int or not 1 <= policy.daily_units <= 10000:
        raise ValueError("invalid daily unit ceiling")
    if billable and not policy.allow_billable:
        raise ValueError("billable operation denied; a separate cost authorization is required")
    session.execute(update(Workspace).where(Workspace.id == workspace_id).values(updated_at=Workspace.updated_at))
    identity = _digest(workspace_id, provider, operation, request_id)[:32]
    key = _digest(identity, fingerprint, units, billable)
    existing = session.get(ConnectorUsage, identity)
    if existing is not None:
        if existing.idempotency_key != key:
            raise ValueError("idempotency request reused with different input")
        if existing.status != "completed":
            raise ValueError("previous request is unresolved; do not retry or fall back automatically")
        return existing, False
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    used = session.scalar(select(func.coalesce(func.sum(ConnectorUsage.units), 0)).where(
        ConnectorUsage.workspace_id == workspace_id, ConnectorUsage.provider == provider,
        ConnectorUsage.created_at >= since, ConnectorUsage.created_at < since + timedelta(days=1),
    ))
    if used + units > policy.daily_units:
        raise ValueError("daily connector unit budget exhausted")
    receipt = ConnectorUsage(id=identity, workspace_id=workspace_id, provider=provider, operation=operation,
                             idempotency_key=key, units=units, billable=billable, status="reserved", created_at=now)
    session.add(receipt); session.flush()
    return receipt, True


def import_feed(session, *, workspace_id, user_id, provider, source_key, content, request_id, policy=UsagePolicy()):
    from .services import TenantService
    TenantService.require_membership(session, workspace_id, user_id)
    if provider not in {"local-feed", "supsub"}:
        raise ValueError("provider import is disabled; preview and license/contract review only")
    if not isinstance(source_key, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", source_key):
        raise ValueError("source key must be a stable non-secret alias, not a URL")
    kind, entries = parse_feed(content)
    if kind == "opml":
        raise ValueError("OPML is preview-only and never creates subscriptions")
    fingerprint = _digest(source_key, content)
    receipt, fresh = reserve_usage(session, workspace_id=workspace_id, provider=provider, operation="file-import",
                                   request_id=request_id, fingerprint=fingerprint, units=max(1, len(entries)), policy=policy)
    if not fresh:
        return {"status": "already_completed", "receipt_id": receipt.id, "imported": 0, "network_requests": 0}
    source_id = f"{provider}:" + _digest(workspace_id, source_key)[:24]
    imported, article_ids = 0, set()
    for entry in entries:
        identity_key = _digest(workspace_id, provider, source_key, entry.external_id)
        identity = session.get(ConnectorIdentity, identity_key)
        if identity is not None:
            article_ids.add(identity.article_id)
            continue
        # URL reuse is restricted to this workspace. Never attach another
        # workspace's private content merely because a URL or title matches.
        article = session.scalar(select(Article).join(WorkspaceArticle, WorkspaceArticle.article_id == Article.id).where(
            WorkspaceArticle.workspace_id == workspace_id, Article.url == entry.url,
        ).limit(1)) if entry.url else None
        if article is None:
            article = Article(id="connector:" + identity_key, mp_id=source_id, title=entry.title, url=entry.url,
                              description=entry.description, content=entry.body, content_html=entry.body,
                              extinfo=json.dumps({"connector_provider": provider, "source_key": source_key}),
                              publish_time=entry.published_at, has_content=int(bool(entry.body)), status=1)
            session.add(article); session.flush()
            session.add(WorkspaceArticle(workspace_id=workspace_id, article_id=article.id, source_id=source_id,
                                         ingestion_source=f"{provider}:file:{kind}"))
            index_article(session, article)
            session.add(WorkflowJob(workspace_id=workspace_id, user_id=user_id, kind="article_analysis",
                                    payload={"article_id": article.id}, idempotency_key="connector-analysis:" + identity_key))
            imported += 1
        # Existing canonical article fields and personal feedback are not
        # overwritten by a second supplier or a repeated fixture import.
        session.add(ConnectorIdentity(identity_key=identity_key, provider=provider, source_id=source_id,
                                       external_id=entry.external_id, article_id=article.id))
        article_ids.add(article.id)
        session.flush()
    receipt.status, receipt.completed_at = "completed", utcnow()
    session.add(OutboxEvent(workspace_id=workspace_id, event_type="connector.import.completed", aggregate_type="connector_usage",
                           aggregate_id=receipt.id, payload={"provider": provider, "imported": imported},
                           idempotency_key="connector-import:" + receipt.id))
    dated_ids = list(session.scalars(select(Article.id).where(Article.id.in_(article_ids), Article.publish_time.is_not(None))))
    queue_reconciliations(session, workspace_ids=(workspace_id,), article_ids=dated_ids,
                          cause=f"connector:{receipt.id}", now=utcnow())
    session.commit()
    return {"status": "completed", "receipt_id": receipt.id, "imported": imported, "network_requests": 0}


def supsub_read_plan(executable, operation, *, source_id=None, source_type="MP", focus_id=None, page=1, query=""):
    """Return argv only, never execute. SupSub 0.4.3 read command contract."""
    if not isinstance(executable, str) or not PurePath(executable).is_absolute() or "\x00" in executable:
        raise ValueError("CLI executable must be an explicit absolute path")
    if operation not in {"sub.list", "sub.contents", "focus.list", "focus.contents", "group.list", "search", "unread"}:
        raise ValueError("command is outside the read-only allowlist")
    argv = [executable, "--api-url", "https://supsub.net", "-o", "json", *operation.split(".")]
    if operation in {"sub.contents", "focus.contents"}:
        identity = source_id if operation == "sub.contents" else focus_id
        if type(identity) is not int or identity < 1 or type(page) is not int or not 1 <= page <= 10000:
            raise ValueError("invalid source/focus identity or page")
        if source_type not in {"MP", "WEBSITE"}:
            raise ValueError("source type has not been verified for this contract")
        argv += ["--source-id" if operation == "sub.contents" else "--id", str(identity)]
        if operation == "sub.contents":
            argv += ["--type", source_type]
        argv += ["--all", "--page", str(page), "--page-size", "20"]
    if operation == "search":
        query = _text(query, 120, "search query")
        if not query or query.startswith("-"):
            raise ValueError("search term cannot be empty or start with an option prefix")
        argv += ["--type", "CONTENT", "--", query]
    return {"argv": argv, "environment": {"SUPSUB_DISABLE_AUTOUPDATER": "1", "SUPSUB_NO_SKILLS_NOTIFIER": "1", "SUPSUB_NO_SPINNER": "1"},
            "version_contract": "0.4.3", "execute": False}


def parse_supsub_output(stdout):
    if not isinstance(stdout, str) or len(stdout.encode()) > MAX_BYTES:
        raise ValueError("CLI output exceeds bounded JSON contract")
    try:
        value = json.loads(stdout)
    except (ValueError, RecursionError) as exc:
        raise ValueError("CLI output must be one JSON document, without banners") from exc
    if not isinstance(value, dict) or value.get("success") is not True or "data" not in value:
        raise ValueError("CLI reported an error or an unknown envelope")
    return value["data"]
