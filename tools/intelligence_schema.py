#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.intelligence.migration import inspect_schema, render_ddl, render_upgrade, readonly_inspection_engine


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Intelligence Hub schema without mutation, or render offline DDL."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="read-only schema inspection")
    inspect_parser.add_argument("--database-url", required=True)
    ddl_parser = subparsers.add_parser("ddl", help="render reviewed offline DDL")
    ddl_parser.add_argument("--dialect", choices=["sqlite", "postgresql", "mysql"], required=True)
    upgrade_parser = subparsers.add_parser("upgrade-sql", help="render frozen versioned SQL; never connect")
    upgrade_parser.add_argument("--dialect", choices=["sqlite", "postgresql"], required=True)
    upgrade_parser.add_argument("--from-revision", default="base", choices=["base", "int_v2_20260824", "int_v3_20260830"])
    args = parser.parse_args()

    if args.command == "ddl":
        print(render_ddl(args.dialect), end="")
        return 0
    if args.command == "upgrade-sql":
        print(render_upgrade(args.dialect, from_revision=args.from_revision), end="")
        return 0

    engine = readonly_inspection_engine(args.database_url)
    try:
        result = inspect_schema(engine, require_revision=True)
    finally:
        engine.dispose()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
