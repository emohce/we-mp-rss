"""Intelligence Hub v2 domain package.

The package is deliberately isolated from the legacy v1 routes.  PostgreSQL (or
SQLite in lite mode) remains the source of truth; Redis and MQTT are optional
coordination transports and may be rebuilt from durable database state.
"""

from .settings import InfrastructureSettings, StorageProfile

__all__ = ["InfrastructureSettings", "StorageProfile"]
