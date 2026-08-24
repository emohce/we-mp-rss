from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class StorageProfile(str, Enum):
    LITE = "lite"
    STANDARD = "standard"
    DISTRIBUTED = "distributed"


@dataclass(frozen=True)
class InfrastructureSettings:
    """Runtime infrastructure selection without importing application config.

    This keeps migrations, tests and command-line tooling deterministic.  Secret
    values are consumed by drivers but are never included in ``describe``.
    """

    profile: StorageProfile = StorageProfile.LITE
    database_url: str = "sqlite:///./data/db.db"
    redis_url: str = ""
    mqtt_url: str = ""
    mqtt_topic_prefix: str = "werss/v2"
    content_backend: str = "local"
    content_root: str = "./data/content"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    public_base_url: str = ""

    @classmethod
    def from_env(
        cls,
        config_getter: Callable[[str, object], object] | None = None,
    ) -> "InfrastructureSettings":
        def read(env_key: str, config_key: str, default: str) -> str:
            if env_key in os.environ:
                return os.environ[env_key]
            if config_getter is not None:
                return str(config_getter(config_key, default) or "")
            return default

        raw_profile = read("STORAGE_PROFILE", "storage.profile", "lite").strip().lower()
        try:
            profile = StorageProfile(raw_profile)
        except ValueError as exc:
            raise ValueError(
                "STORAGE_PROFILE must be lite, standard, or distributed"
            ) from exc
        return cls(
            profile=profile,
            database_url=read("DB", "db", "sqlite:///./data/db.db").strip(),
            redis_url=read("REDIS_URL", "redis.url", "").strip(),
            mqtt_url=read("MQTT_URL", "mqtt.url", "").strip(),
            mqtt_topic_prefix=read(
                "MQTT_TOPIC_PREFIX", "mqtt.topic_prefix", "werss/v2"
            ).strip("/"),
            content_backend=read(
                "CONTENT_BACKEND", "storage.content_backend", "local"
            ).strip().lower(),
            content_root=read(
                "CONTENT_ROOT", "storage.content_root", "./data/content"
            ).strip(),
            s3_bucket=read("S3_BUCKET", "storage.s3_bucket", "").strip(),
            s3_endpoint_url=read(
                "S3_ENDPOINT_URL", "storage.s3_endpoint_url", ""
            ).strip(),
            public_base_url=read(
                "PUBLIC_BASE_URL", "intelligence.public_base_url", ""
            ).rstrip("/"),
        )

    def validate(self) -> list[str]:
        issues: list[str] = []
        if self.profile is StorageProfile.LITE:
            if not self.database_url.startswith("sqlite"):
                issues.append("lite profile requires a SQLite DB URL")
        else:
            if not self.database_url.startswith(("postgresql://", "postgresql+")):
                issues.append("standard/distributed profile requires PostgreSQL")
            if not self.redis_url.startswith(("redis://", "rediss://")):
                issues.append("standard/distributed profile requires REDIS_URL")
        if self.profile is StorageProfile.DISTRIBUTED and not self.mqtt_url.startswith(
            ("mqtt://", "mqtts://")
        ):
            issues.append("distributed profile requires MQTT_URL")
        if self.content_backend not in {"local", "s3"}:
            issues.append("CONTENT_BACKEND must be local or s3")
        if self.content_backend == "s3" and not self.s3_bucket:
            issues.append("S3_BUCKET is required for the s3 content backend")
        if not self.mqtt_topic_prefix:
            issues.append("MQTT_TOPIC_PREFIX cannot be empty")
        return issues

    def describe(self) -> dict[str, object]:
        """Return a secret-free diagnostic projection."""

        return {
            "profile": self.profile.value,
            "database": self.database_url.split(":", 1)[0],
            "redis_enabled": bool(self.redis_url),
            "mqtt_enabled": bool(self.mqtt_url),
            "mqtt_topic_prefix": self.mqtt_topic_prefix,
            "content_backend": self.content_backend,
            "public_base_url_configured": bool(self.public_base_url),
        }
