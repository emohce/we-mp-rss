from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .events import EventEnvelope, EventPublisher, RedisCoordinator
from .idempotency import normalize_idempotency_key
from .models import OutboxEvent, utcnow


@dataclass(frozen=True)
class ClaimedOutboxEvent:
    id: str
    lease_token: str
    workspace_id: str | None
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict
    attempts: int
    created_at: datetime

    def envelope(self) -> EventEnvelope:
        return EventEnvelope(
            event_id=self.id,
            event_type=self.event_type,
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            workspace_id=self.workspace_id,
            created_at=self.created_at.isoformat() + "Z",
            attributes=self.payload,
        )


class OutboxRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        coordinator: RedisCoordinator | None = None,
    ):
        self.session_factory = session_factory
        self.coordinator = coordinator

    def enqueue(
        self,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        workspace_id: str | None = None,
        payload: dict | None = None,
        available_at: datetime | None = None,
    ) -> tuple[OutboxEvent, bool]:
        normalized_key = normalize_idempotency_key(idempotency_key, 160)
        with self.session_factory() as session:
            existing = session.scalar(
                select(OutboxEvent).where(OutboxEvent.idempotency_key == normalized_key)
            )
            if existing:
                return existing, False
            event = OutboxEvent(
                workspace_id=workspace_id,
                event_type=event_type[:100],
                aggregate_type=aggregate_type[:60],
                aggregate_id=aggregate_id[:255],
                payload=payload or {},
                idempotency_key=normalized_key,
                available_at=available_at or utcnow(),
            )
            session.add(event)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(OutboxEvent).where(OutboxEvent.idempotency_key == normalized_key)
                )
                if existing:
                    return existing, False
                raise
            session.refresh(event)
            event_id = event.id
        if self.coordinator:
            self.coordinator.wake("outbox", event_id)
        return event, True

    def claim_next(
        self,
        *,
        lease_seconds: int = 60,
        now: datetime | None = None,
    ) -> ClaimedOutboxEvent | None:
        now = now or utcnow()
        with self.session_factory() as session:
            session.execute(update(OutboxEvent).where(
                OutboxEvent.state == "publishing", OutboxEvent.lease_expires_at <= now,
                OutboxEvent.attempts >= OutboxEvent.max_attempts,
            ).values(state="failed", lease_token="", lease_expires_at=None, last_error="lease_expired"))
            session.commit()
        for _ in range(3):
            with self.session_factory() as session:
                event_id = session.scalar(
                    select(OutboxEvent.id)
                    .where(
                        OutboxEvent.available_at <= now,
                        OutboxEvent.attempts < OutboxEvent.max_attempts,
                        or_(
                            OutboxEvent.state == "pending",
                            and_(
                                OutboxEvent.state == "publishing",
                                OutboxEvent.lease_expires_at.is_not(None),
                                OutboxEvent.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .order_by(OutboxEvent.available_at, OutboxEvent.created_at)
                    .limit(1)
                )
                if not event_id:
                    return None
                token = secrets.token_urlsafe(32)
                result = session.execute(
                    update(OutboxEvent)
                    .where(
                        OutboxEvent.id == event_id,
                        or_(
                            OutboxEvent.state == "pending",
                            and_(
                                OutboxEvent.state == "publishing",
                                OutboxEvent.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .values(
                        state="publishing",
                        attempts=OutboxEvent.attempts + 1,
                        lease_token=token,
                        lease_expires_at=now + timedelta(seconds=max(10, lease_seconds)),
                    )
                )
                if result.rowcount != 1:
                    session.rollback()
                    continue
                session.commit()
                event = session.get(OutboxEvent, event_id)
                if event is None:
                    return None
                return ClaimedOutboxEvent(
                    id=event.id,
                    lease_token=token,
                    workspace_id=event.workspace_id,
                    event_type=event.event_type,
                    aggregate_type=event.aggregate_type,
                    aggregate_id=event.aggregate_id,
                    payload=event.payload or {},
                    attempts=event.attempts,
                    created_at=event.created_at,
                )
        return None

    def mark_delivered(self, event_id: str, lease_token: str) -> bool:
        with self.session_factory() as session:
            result = session.execute(
                update(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.state == "publishing",
                    OutboxEvent.lease_token == lease_token,
                    OutboxEvent.lease_expires_at > utcnow(),
                )
                .values(
                    state="delivered",
                    delivered_at=utcnow(),
                    lease_token="",
                    lease_expires_at=None,
                    last_error="",
                )
            )
            session.commit()
            return result.rowcount == 1

    def mark_retry(self, event_id: str, lease_token: str, error: str) -> bool:
        with self.session_factory() as session:
            event = session.scalar(
                select(OutboxEvent).where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.state == "publishing",
                    OutboxEvent.lease_token == lease_token,
                    OutboxEvent.lease_expires_at > utcnow(),
                )
            )
            if event is None:
                return False
            delays = (5, 15, 30, 60, 120, 300, 600, 1800)
            delay = delays[min(max(event.attempts - 1, 0), len(delays) - 1)]
            result = session.execute(update(OutboxEvent).where(
                OutboxEvent.id == event_id, OutboxEvent.state == "publishing",
                OutboxEvent.lease_token == lease_token, OutboxEvent.lease_expires_at > utcnow(),
            ).values(state="failed" if event.attempts >= event.max_attempts else "pending",
                     available_at=utcnow() + timedelta(seconds=delay), lease_token="", lease_expires_at=None,
                     last_error=error[:500]))
            session.commit()
            return result.rowcount == 1


class OutboxDispatcher:
    def __init__(self, repository: OutboxRepository, publisher: EventPublisher):
        self.repository = repository
        self.publisher = publisher

    def dispatch_once(self) -> bool:
        if getattr(self.publisher, "transport_enabled", True) is False:
            # Lite/Standard retain local events; no fake 'delivered' receipt.
            return False
        claimed = self.repository.claim_next()
        if claimed is None:
            return False
        try:
            self.publisher.publish(claimed.envelope())
        except Exception as exc:
            self.repository.mark_retry(claimed.id, claimed.lease_token, type(exc).__name__)
            return False
        return self.repository.mark_delivered(claimed.id, claimed.lease_token)
