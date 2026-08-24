from __future__ import annotations

import hashlib


def normalize_idempotency_key(value: str, max_length: int) -> str:
    """Keep short keys readable and hash long suffixes without collisions."""

    if not value:
        raise ValueError("idempotency_key must not be empty")
    digest_length = 64
    if max_length <= digest_length + 1:
        raise ValueError("idempotency key column is too short")
    if len(value) <= max_length:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    prefix_length = max_length - digest_length - 1
    return f"{value[:prefix_length]}:{digest}"
