from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import Engine, inspect
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from core.models.article import Article  # noqa: F401 - registers the legacy FK target
from core.models.base import Base

from . import models as intelligence_models  # noqa: F401 - registers all int_ tables


SCHEMA_REVISION = "intelligence-v2-20260824-1"
LEGACY_REQUIREMENTS = {"articles"}


def intelligence_tables():
    return [
        table
        for table in Base.metadata.sorted_tables
        if table.name.startswith("int_")
    ]


@dataclass(frozen=True)
class SchemaInspection:
    revision: str
    dialect: str
    ready: bool
    missing_legacy_tables: tuple[str, ...]
    missing_tables: tuple[str, ...]
    unexpected_intelligence_tables: tuple[str, ...]
    missing_columns: dict[str, tuple[str, ...]]
    unexpected_columns: dict[str, tuple[str, ...]]

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_schema(engine: Engine) -> SchemaInspection:
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    expected_tables = {table.name: table for table in intelligence_tables()}
    missing_tables = sorted(set(expected_tables) - actual_tables)
    unexpected_tables = sorted(
        name for name in actual_tables if name.startswith("int_") and name not in expected_tables
    )
    missing_columns: dict[str, tuple[str, ...]] = {}
    unexpected_columns: dict[str, tuple[str, ...]] = {}
    for table_name, table in expected_tables.items():
        if table_name not in actual_tables:
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        expected_columns = {column.name for column in table.columns}
        missing = tuple(sorted(expected_columns - actual_columns))
        unexpected = tuple(sorted(actual_columns - expected_columns))
        if missing:
            missing_columns[table_name] = missing
        if unexpected:
            unexpected_columns[table_name] = unexpected
    missing_legacy = tuple(sorted(LEGACY_REQUIREMENTS - actual_tables))
    ready = not (missing_legacy or missing_tables or missing_columns)
    return SchemaInspection(
        revision=SCHEMA_REVISION,
        dialect=engine.dialect.name,
        ready=ready,
        missing_legacy_tables=missing_legacy,
        missing_tables=tuple(missing_tables),
        unexpected_intelligence_tables=tuple(unexpected_tables),
        missing_columns=missing_columns,
        unexpected_columns=unexpected_columns,
    )


def render_ddl(dialect_name: str) -> str:
    dialects = {
        "sqlite": sqlite.dialect(),
        "postgresql": postgresql.dialect(),
        "mysql": mysql.dialect(),
    }
    if dialect_name not in dialects:
        raise ValueError("dialect must be sqlite, postgresql, or mysql")
    dialect = dialects[dialect_name]
    statements = [
        f"-- WeRSS Intelligence Hub schema {SCHEMA_REVISION}",
        "-- Review before execution. This file contains DDL only.",
    ]
    for table in intelligence_tables():
        statements.append(str(CreateTable(table).compile(dialect=dialect)).rstrip() + ";")
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).rstrip() + ";")
    return "\n\n".join(statements) + "\n"
