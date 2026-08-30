from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from .collection_state import CollectionState, LeaseLost, SourceBusy
from .content import prepare_objects
from .jobs import ClaimedJob, JobRepository
from .models import CollectorAccount, utcnow
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
        content_store=None,
    ):
        self.session_factory = session_factory
        self.jobs = jobs
        self.rate_limits = rate_limits
        self.adapters = adapters
        self.max_articles_per_page = min(max(max_articles_per_page, 1), 500)
        self.state = CollectionState(session_factory)
        self.content_store = content_store

    def run_once(self, *, now: datetime | None = None) -> str:
        clock = (lambda: now) if now is not None else utcnow
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
        with self.session_factory() as session:
            account = session.get(CollectorAccount, claimed.account_id)
            if (account is None or account.status not in {"healthy", "probe"}
                    or account.provider != claimed.provider
                    or account.workspace_id not in {None, claimed.workspace_id}):
                self.jobs.fail(job_id=claimed.id, lease_token=claimed.lease_token,
                               error_code="account_disabled", error_message="collector account is unavailable")
                return "account_disabled"
        adapter = self.adapters.get(claimed.provider)
        if adapter is None:
            self.jobs.fail(
                job_id=claimed.id,
                lease_token=claimed.lease_token,
                error_code="adapter_not_configured",
                error_message="collector adapter is not configured",
            )
            return "adapter_not_configured"

        try:
            attempt = self.state.begin_page(claimed, now)
        except SourceBusy:
            self.jobs.defer(claimed, due_at=now + timedelta(seconds=60), error_code="source_busy")
            return "source_deferred"
        except LeaseLost:
            self.jobs.fail(job_id=claimed.id, lease_token=claimed.lease_token,
                           error_code="checkpoint_superseded", error_message="checkpoint or lease advanced")
            return "lease_lost"

        admitted, snapshot = self.rate_limits.allow_request(
            claimed.provider,
            claimed.account_id,
            source_id=claimed.source_id,
            now=now,
        )
        if not admitted:
            due_at = snapshot.cooldown_until or (now + timedelta(minutes=1))
            self.jobs.defer(claimed, due_at=due_at, error_code="local_rate_budget")
            return "rate_deferred"

        try:
            page = adapter.fetch_page(
                source_id=claimed.source_id,
                cursor=attempt.cursor,
                page_budget=1,
            )
            if len(page.articles) > self.max_articles_per_page:
                raise CollectorError(
                    "page_too_large",
                    safe_message="collector page exceeded the configured article limit",
                )
            objects = prepare_objects(page, self.content_store)
            result = self.state.finish_page(claimed, attempt, page, clock(), stored_objects=objects)
            self.rate_limits.apply_signal(
                claimed.provider,
                claimed.account_id,
                RateSignal.SUCCESS,
                now=now,
            )
            return result
        except LeaseLost:
            return "lease_lost"
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
