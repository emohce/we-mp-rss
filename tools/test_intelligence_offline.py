#!/usr/bin/env python3
"""Run the focused contract suite without sockets, child processes or user DBs.

The audit guard is installed before any application/test import. A swallowed
violation still fails the run. This is local contract evidence, not runtime
acceptance of PostgreSQL, Redis, MQTT, providers or browser interaction.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = Path(tempfile.gettempdir()).resolve()
violations: list[str] = []
BLOCKED = {
    "socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname",
    "socket.gethostbyaddr", "socket.sendto", "socket.sendmsg",
    "subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.exec",
}


def deny_external_io(event: str, args: tuple) -> None:
    blocked = event in BLOCKED
    if event == "sqlite3.connect":
        database = str(args[0])
        # Only in-memory or temporary test fixtures. Never create/open a user DB.
        blocked = database != ":memory:" and not (
            not database.startswith("file:") and
            Path(database).resolve().is_relative_to(TEMP_ROOT)
        )
    if blocked:
        violations.append(event)  # Never retain addresses, DSNs or arguments.
        raise RuntimeError(f"offline contract guard blocked {event}")


def main() -> int:
    os.environ["DB"] = "sqlite://"
    os.environ["REDIS_URL"] = ""
    # urllib3 otherwise probes IPv6 availability by binding a loopback socket at
    # import time. Disable that optional probe; do not weaken the bind guard.
    socket.has_ipv6 = False
    sys.path.insert(0, str(ROOT))
    sys.addaudithook(deny_external_io)
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "core/intelligence"), pattern="test_*.py", top_level_dir=str(ROOT),
    )
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    unexpected_runtime = [name for name in ("jobs", "core.queue", "core.redis_client") if name in sys.modules]
    print(f"Offline guard: blocked_attempts={len(violations)}, legacy_runtime_imports={len(unexpected_runtime)}")
    if violations or unexpected_runtime:
        print(f"Blocked event types: {sorted(set(violations))}; unexpected modules: {unexpected_runtime}")
        print("Offline isolation failed; no external-service acceptance is claimed.")
    return 0 if result.wasSuccessful() and not violations and not unexpected_runtime else 1


if __name__ == "__main__":
    raise SystemExit(main())
