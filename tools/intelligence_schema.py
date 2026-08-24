#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine

from core.intelligence.migration import inspect_schema, render_ddl


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Intelligence Hub schema without mutation, or render offline DDL."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="read-only schema inspection")
    inspect_parser.add_argument("--database-url", required=True)
    ddl_parser = subparsers.add_parser("ddl", help="render reviewed offline DDL")
    ddl_parser.add_argument("--dialect", choices=["sqlite", "postgresql", "mysql"], required=True)
    args = parser.parse_args()

    if args.command == "ddl":
        print(render_ddl(args.dialect), end="")
        return 0

    engine = create_engine(args.database_url, pool_pre_ping=True)
    try:
        result = inspect_schema(engine)
    finally:
        engine.dispose()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
