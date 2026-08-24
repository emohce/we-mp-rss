from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    workspace_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    attributes: dict[str, Any] = field(default_factory=dict)

    def compact_payload(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":")).encode()


class EventPublisher(Protocol):
    def publish(self, event: EventEnvelope) -> None: ...


class NullPublisher:
    def publish(self, event: EventEnvelope) -> None:
        return None


class RedisCoordinator:
    """Redis acceleration layer; durable state must never live only here."""

    def __init__(self, redis_url: str, namespace: str = "werss:v2"):
        self.redis_url = redis_url
        self.namespace = namespace.rstrip(":")
        self._client = None

    def _get_client(self):
        if not self.redis_url:
            return None
        if self._client is None:
            import redis

            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        return self._client

    def health(self) -> bool:
        try:
            client = self._get_client()
            return bool(client and client.ping())
        except Exception:
            return False

    def wake(self, channel: str, event_id: str) -> bool:
        try:
            client = self._get_client()
            if not client:
                return False
            client.publish(f"{self.namespace}:wake:{channel}", event_id)
            return True
        except Exception:
            return False

    def get_json(self, key: str) -> object | None:
        try:
            client = self._get_client()
            if not client:
                return None
            raw = client.get(f"{self.namespace}:cache:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def set_json(self, key: str, value: object, ttl_seconds: int = 300) -> bool:
        try:
            client = self._get_client()
            if not client:
                return False
            client.set(
                f"{self.namespace}:cache:{key}",
                json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str),
                ex=max(1, ttl_seconds),
            )
            return True
        except Exception:
            return False

    def consume_budget(
        self,
        name: str,
        *,
        capacity: int,
        refill_per_second: float,
        tokens: int = 1,
    ) -> bool | None:
        """Atomically consume a Redis token bucket, or return None on outage."""

        if capacity < 1 or refill_per_second <= 0 or tokens < 1:
            raise ValueError("invalid token bucket settings")
        script = """
        local current_time = redis.call('TIME')
        local now = tonumber(current_time[1]) + tonumber(current_time[2]) / 1000000
        local values = redis.call('HMGET', KEYS[1], 'tokens', 'updated')
        local available = tonumber(values[1]) or tonumber(ARGV[1])
        local updated = tonumber(values[2]) or now
        available = math.min(tonumber(ARGV[1]), available + (now - updated) * tonumber(ARGV[2]))
        local allowed = available >= tonumber(ARGV[3])
        if allowed then available = available - tonumber(ARGV[3]) end
        redis.call('HSET', KEYS[1], 'tokens', available, 'updated', now)
        local ttl = math.ceil(tonumber(ARGV[1]) / tonumber(ARGV[2]) * 2)
        redis.call('EXPIRE', KEYS[1], math.max(1, ttl))
        return allowed and 1 or 0
        """
        try:
            client = self._get_client()
            if not client:
                return None
            return bool(
                client.eval(
                    script,
                    1,
                    f"{self.namespace}:budget:{name}",
                    capacity,
                    refill_per_second,
                    tokens,
                )
            )
        except Exception:
            return None

    def acquire_lock(self, name: str, ttl_seconds: int = 30) -> str | None:
        try:
            client = self._get_client()
            if not client:
                return None
            token = secrets.token_urlsafe(24)
            acquired = client.set(
                f"{self.namespace}:lock:{name}", token, ex=max(1, ttl_seconds), nx=True
            )
            return token if acquired else None
        except Exception:
            return None

    def release_lock(self, name: str, token: str) -> bool:
        if not token:
            return False
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
          return redis.call('del', KEYS[1])
        end
        return 0
        """
        try:
            client = self._get_client()
            if not client:
                return False
            return bool(client.eval(script, 1, f"{self.namespace}:lock:{name}", token))
        except Exception:
            return False


class MqttPublisher:
    """QoS 1 event transport carrying only compact routing envelopes."""

    def __init__(self, mqtt_url: str, topic_prefix: str = "werss/v2"):
        parsed = urlparse(mqtt_url)
        if parsed.scheme not in {"mqtt", "mqtts"} or not parsed.hostname:
            raise ValueError("MQTT_URL must use mqtt:// or mqtts://")
        self.url = parsed
        self.topic_prefix = topic_prefix.strip("/")
        self._client = None

    def _connect(self):
        if self._client is not None:
            return self._client
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("paho-mqtt is required for MQTT transport") from exc
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.url.username:
            client.username_pw_set(self.url.username, self.url.password or "")
        if self.url.scheme == "mqtts":
            client.tls_set()
        client.connect(self.url.hostname, self.url.port or (8883 if self.url.scheme == "mqtts" else 1883), 30)
        client.loop_start()
        self._client = client
        return client

    def publish(self, event: EventEnvelope) -> None:
        client = self._connect()
        topic = f"{self.topic_prefix}/events/{event.event_type.replace('.', '/')}"
        info = client.publish(topic, event.compact_payload(), qos=1, retain=False)
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            raise RuntimeError("MQTT publish did not complete")

    def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
