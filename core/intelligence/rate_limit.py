from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from .events import RedisCoordinator
from .idempotency import normalize_idempotency_key
from .models import RateLimitLedger, RequestBudget


class RateState(str, Enum):
    HEALTHY = "healthy"
    SOFT_LIMIT = "soft_limit"
    COOLDOWN = "cooldown"
    PROBE = "probe"
    DISABLED = "disabled"


class RateSignal(str, Enum):
    SUCCESS = "success"
    RATE_LIMITED = "rate_limited"
    CAPTCHA = "captcha"
    AUTH_INVALID = "auth_invalid"
    TRANSIENT_ERROR = "transient_error"
    PROBE_DUE = "probe_due"


@dataclass(frozen=True)
class RateSnapshot:
    state: RateState = RateState.HEALTHY
    failure_count: int = 0
    cooldown_until: datetime | None = None
    last_signal: str = ""

    def may_request(self, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        if self.state is RateState.DISABLED:
            return False
        if self.state is RateState.COOLDOWN:
            return bool(self.cooldown_until and now >= self.cooldown_until)
        return self.state in {RateState.HEALTHY, RateState.PROBE}


class RateLimitPolicy:
    BACKOFF_MINUTES = (15, 30, 60, 120, 240, 360)

    @classmethod
    def apply(
        cls,
        current: RateSnapshot,
        signal: RateSignal,
        *,
        now: datetime | None = None,
        retry_after_seconds: int | None = None,
    ) -> RateSnapshot:
        now = now or datetime.utcnow()
        if signal is RateSignal.SUCCESS:
            return RateSnapshot(RateState.HEALTHY, 0, None, signal.value)
        if signal is RateSignal.AUTH_INVALID:
            return RateSnapshot(RateState.DISABLED, current.failure_count + 1, None, signal.value)
        if signal is RateSignal.PROBE_DUE:
            if current.state is RateState.COOLDOWN and current.cooldown_until and now >= current.cooldown_until:
                return RateSnapshot(RateState.PROBE, current.failure_count, None, signal.value)
            return current

        failure_count = current.failure_count + 1
        if retry_after_seconds is not None and retry_after_seconds > 0:
            delay = timedelta(seconds=min(retry_after_seconds, 24 * 60 * 60))
        elif signal is RateSignal.CAPTCHA:
            delay = timedelta(hours=6)
        else:
            index = min(failure_count - 1, len(cls.BACKOFF_MINUTES) - 1)
            delay = timedelta(minutes=cls.BACKOFF_MINUTES[index])
        return RateSnapshot(
            RateState.COOLDOWN,
            failure_count,
            now + delay,
            signal.value,
        )


def classify_provider_error(code: str | int | None, http_status: int | None = None) -> RateSignal:
    normalized = str(code or "").lower()
    if http_status == 429 or normalized in {"200013", "rate_limited", "too_many_requests"}:
        return RateSignal.RATE_LIMITED
    if http_status == 401 or normalized in {"200003", "invalid_session", "auth_invalid", "401"}:
        return RateSignal.AUTH_INVALID
    if normalized in {"captcha", "verification_required", "risk_control"}:
        return RateSignal.CAPTCHA
    if normalized in {"0", "ok", "success"} or (http_status is not None and 200 <= http_status < 300):
        return RateSignal.SUCCESS
    return RateSignal.TRANSIENT_ERROR


class RateLimitRepository:
    """Durable provider state with optional Redis admission control."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        coordinator: RedisCoordinator | None = None,
    ):
        self.session_factory = session_factory
        self.coordinator = coordinator

    @staticmethod
    def _snapshot_from_ledger(ledger: RateLimitLedger) -> RateSnapshot:
        try:
            state = RateState(ledger.state)
        except ValueError:
            state = RateState.COOLDOWN
        return RateSnapshot(
            state=state,
            failure_count=ledger.failure_count,
            cooldown_until=ledger.cooldown_until,
            last_signal=ledger.last_signal,
        )

    def snapshot(self, provider: str, account_id: str) -> RateSnapshot:
        with self.session_factory() as session:
            ledger = session.scalar(
                select(RateLimitLedger).where(
                    RateLimitLedger.provider == provider,
                    RateLimitLedger.account_id == account_id,
                )
            )
            if ledger is None:
                return RateSnapshot()
            return self._snapshot_from_ledger(ledger)

    def apply_signal(
        self,
        provider: str,
        account_id: str,
        signal: RateSignal,
        *,
        now: datetime | None = None,
        retry_after_seconds: int | None = None,
    ) -> RateSnapshot:
        now = now or datetime.utcnow()
        with self.session_factory() as session:
            ledger = session.scalar(
                select(RateLimitLedger).where(
                    RateLimitLedger.provider == provider,
                    RateLimitLedger.account_id == account_id,
                )
            )
            current = self._snapshot_from_ledger(ledger) if ledger is not None else RateSnapshot()
            if (signal is RateSignal.SUCCESS and ledger is not None
                    and ledger.updated_at > now and current.state in {RateState.COOLDOWN, RateState.DISABLED}):
                return current  # an older in-flight success cannot erase newer risk evidence
            result = RateLimitPolicy.apply(
                current,
                signal,
                now=now,
                retry_after_seconds=retry_after_seconds,
            )
            if ledger is None:
                ledger = RateLimitLedger(provider=provider, account_id=account_id)
                session.add(ledger)
            ledger.state = result.state.value
            ledger.failure_count = result.failure_count
            ledger.cooldown_until = result.cooldown_until
            ledger.last_signal = result.last_signal
            ledger.updated_at = now
            session.commit()
            return result

    def allow_request(
        self,
        provider: str,
        account_id: str,
        *,
        source_id: str = "",
        capacity: int = 1,
        refill_per_second: float = 1 / 30,
        now: datetime | None = None,
    ) -> tuple[bool, RateSnapshot]:
        now = now or datetime.utcnow()
        snapshot = self.snapshot(provider, account_id)
        if snapshot.state is RateState.COOLDOWN and snapshot.may_request(now):
            snapshot = self.apply_signal(provider, account_id, RateSignal.PROBE_DUE, now=now)
        if not snapshot.may_request(now):
            return False, snapshot
        # Always reserve in the durable DB, including Lite without Redis.
        # These intervals are conservative engineering policy, NOT WeChat quotas.
        scopes = [(f"provider:{provider}", 6), (f"account:{provider}:{account_id}", 30)]
        if source_id:
            scopes.append((f"source:{provider}:{source_id}", 30))
        allowed, retry_at = self._reserve(scopes, now)
        if not allowed:
            return False, RateSnapshot(snapshot.state, snapshot.failure_count, retry_at, "local_budget")
        if self.coordinator and self.coordinator.redis_url:
            admitted = self.coordinator.consume_budget(
                f"{provider}:{account_id}",
                capacity=capacity,
                refill_per_second=refill_per_second,
            )
            if admitted is not True:
                return False, snapshot
        return True, snapshot

    def _reserve(self, scopes, now: datetime) -> tuple[bool, datetime | None]:
        try:
            with self.session_factory() as session:
                for raw_key, seconds in sorted(scopes):
                    key = normalize_idempotency_key(raw_key, 240)
                    budget = session.get(RequestBudget, key)
                    if budget is None:
                        budget = RequestBudget(scope_key=key, next_allowed_at=now, version=0,
                                               admitted_count=0)
                        session.add(budget)
                        session.flush()
                    if budget.next_allowed_at > now:
                        retry_at = budget.next_allowed_at
                        session.rollback()  # all scopes are one admission, never partial
                        return False, retry_at
                    result = session.execute(update(RequestBudget).where(
                        RequestBudget.scope_key == key, RequestBudget.version == budget.version,
                        RequestBudget.next_allowed_at <= now,
                    ).values(version=budget.version + 1, admitted_count=budget.admitted_count + 1,
                             next_allowed_at=now + timedelta(seconds=seconds)))
                    if result.rowcount != 1:
                        session.rollback()
                        return False, now + timedelta(seconds=seconds)
                session.commit()
                return True, None
        except (IntegrityError, OperationalError):
            # CAS/creation conflict or SQLite's bounded writer lock: defer, never bypass.
            return False, now + timedelta(seconds=30)
