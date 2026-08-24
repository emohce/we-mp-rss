from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.article import Article

from .jobs import ClaimedJob, JobRepository
from .models import CollectorAccount, CollectorCursor, utcnow
from .rate_limit import (
    RateLimitRepository,
    RateSignal,
    classify_provider_error,
)


@dataclass(frozen=True)
class CollectedPage:
    articles: tuple[dict, ...]
    next_cursor: dict
    ingestion_source: str


class CollectorAdapter(Protocol):
    def fetch_page(
        self,
        *,
        source_id: str,
        cursor: dict,
        page_budget: int,
    ) -> CollectedPage: ...


class CollectorError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
        retry_after_seconds: int | None = None,
        safe_message: str = "provider request failed",
    ):
        super().__init__(safe_message)
        self.code = str(code)[:80]
        self.http_status = http_status
        self.retry_after_seconds = retry_after_seconds
        self.safe_message = safe_message[:500]


class CollectionWorker:
    """One-page collector runner. Network behavior is supplied by an adapter."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        jobs: JobRepository,
        rate_limits: RateLimitRepository,
        adapters: dict[str, CollectorAdapter],
        max_articles_per_page: int = 100,
    ):
        self.session_factory = session_factory
        self.jobs = jobs
        self.rate_limits = rate_limits
        self.adapters = adapters
        self.max_articles_per_page = min(max(max_articles_per_page, 1), 500)

    def run_once(self, *, now: datetime | None = None) -> str:
        now = now or utcnow()
        claimed = self.jobs.claim_next(now=now)
        if claimed is None:
            return "idle"
        if not claimed.account_id:
            self._retry_or_fail(
                claimed,
                due_at=now + timedelta(minutes=30),
                error_code="account_not_configured",
                error_message="collector account is not configured",
            )
            return "account_not_configured"
        adapter = self.adapters.get(claimed.provider)
        if adapter is None:
            self.jobs.fail(
                job_id=claimed.id,
                lease_token=claimed.lease_token,
                error_code="adapter_not_configured",
                error_message="collector adapter is not configured",
            )
            return "adapter_not_configured"

        admitted, snapshot = self.rate_limits.allow_request(
            claimed.provider,
            claimed.account_id,
            now=now,
        )
        if not admitted:
            due_at = snapshot.cooldown_until or (now + timedelta(minutes=1))
            self._retry_or_fail(
                claimed,
                due_at=due_at,
                error_code="local_rate_budget",
                error_message="collector request deferred by rate policy",
            )
            return "rate_deferred"

        cursor = self._cursor(claimed.account_id, claimed.source_id)
        try:
            page = adapter.fetch_page(
                source_id=claimed.source_id,
                cursor=cursor,
                page_budget=1,
            )
            if len(page.articles) > self.max_articles_per_page:
                raise CollectorError(
                    "page_too_large",
                    safe_message="collector page exceeded the configured article limit",
                )
            article_ids = self._persist_articles(claimed, page)
            self.rate_limits.apply_signal(
                claimed.provider,
                claimed.account_id,
                RateSignal.SUCCESS,
                now=now,
            )
            self.jobs.complete_page(
                job_id=claimed.id,
                lease_token=claimed.lease_token,
                account_id=claimed.account_id,
                next_cursor=page.next_cursor,
                article_ids=article_ids,
                ingestion_source=page.ingestion_source[:40],
            )
            return "completed"
        except CollectorError as exc:
            signal = classify_provider_error(exc.code, exc.http_status)
            rate_snapshot = self.rate_limits.apply_signal(
                claimed.provider,
                claimed.account_id,
                signal,
                now=now,
                retry_after_seconds=exc.retry_after_seconds,
            )
            if signal is RateSignal.AUTH_INVALID:
                self._disable_account(claimed.account_id, exc.code)
                self.jobs.fail(
                    job_id=claimed.id,
                    lease_token=claimed.lease_token,
                    error_code=exc.code,
                    error_message=exc.safe_message,
                )
                return "account_disabled"
            due_at = rate_snapshot.cooldown_until or (now + timedelta(minutes=15))
            self._retry_or_fail(
                claimed,
                due_at=due_at,
                error_code=exc.code,
                error_message=exc.safe_message,
            )
            return "retry"
        except Exception as exc:
            self._retry_or_fail(
                claimed,
                due_at=now + timedelta(minutes=15),
                error_code="collector_internal_error",
                error_message=type(exc).__name__,
            )
            return "retry"

    def _disable_account(self, account_id: str, error_code: str) -> None:
        with self.session_factory() as session:
            account = session.get(CollectorAccount, account_id)
            if account is None:
                return
            account.status = "disabled"
            account.last_error_code = error_code[:80]
            session.commit()

    def _cursor(self, account_id: str, source_id: str) -> dict:
        with self.session_factory() as session:
            cursor = session.scalar(
                select(CollectorCursor).where(
                    CollectorCursor.account_id == account_id,
                    CollectorCursor.source_id == source_id,
                )
            )
            return dict(cursor.cursor or {}) if cursor else {}

    def _persist_articles(self, claimed: ClaimedJob, page: CollectedPage) -> list[str]:
        allowed_columns = {column.name for column in Article.__table__.columns} - {"id"}
        seen: set[str] = set()
        with self.session_factory() as session:
            for raw in page.articles:
                article_id = str(raw.get("id") or "").strip()
                if not article_id or len(article_id) > 255 or article_id in seen:
                    raise CollectorError(
                        "invalid_article_id",
                        safe_message="collector returned an invalid or duplicate article id",
                    )
                seen.add(article_id)
                article = session.get(Article, article_id)
                values = {
                    key: value
                    for key, value in raw.items()
                    if key in allowed_columns and value is not None
                }
                values.setdefault("mp_id", claimed.source_id)
                if article is None:
                    session.add(Article(id=article_id, **values))
                else:
                    for key, value in values.items():
                        setattr(article, key, value)
            session.commit()
        return list(seen)

    def _retry_or_fail(
        self,
        claimed: ClaimedJob,
        *,
        due_at: datetime,
        error_code: str,
        error_message: str,
    ) -> None:
        if claimed.attempts >= claimed.max_attempts:
            self.jobs.fail(
                job_id=claimed.id,
                lease_token=claimed.lease_token,
                error_code=error_code,
                error_message=error_message,
            )
            return
        self.jobs.retry(
            job_id=claimed.id,
            lease_token=claimed.lease_token,
            due_at=due_at,
            error_code=error_code,
            error_message=error_message,
        )
