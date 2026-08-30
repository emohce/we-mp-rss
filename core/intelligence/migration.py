from __future__ import annotations

from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path

from sqlalchemy import Engine, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.engine import make_url, URL
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from core.models.article import Article  # noqa: F401 - registers the legacy FK target
from core.models.base import Base

from . import models as intelligence_models  # noqa: F401 - registers all int_ tables


SCHEMA_REVISION = "int_v3_20260830"
BASELINE_REVISION = "int_v2_20260824"
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
    applied_revisions: tuple[str, ...]
    revision_matches: bool
    missing_unique_constraints: dict[str, tuple[str, ...]]
    missing_indexes: dict[str, tuple[str, ...]]
    missing_legacy_columns: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_schema(engine: Engine, *, require_revision: bool = False) -> SchemaInspection:
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names())
    expected_tables = {table.name: table for table in intelligence_tables()}
    missing_tables = sorted(set(expected_tables) - actual_tables)
    unexpected_tables = sorted(
        name for name in actual_tables if name.startswith("int_") and name not in expected_tables
        and name != "int_schema_version" and not name.startswith("int_search_fts")
    )
    missing_columns: dict[str, tuple[str, ...]] = {}
    unexpected_columns: dict[str, tuple[str, ...]] = {}
    missing_unique: dict[str, tuple[str, ...]] = {}
    missing_indexes: dict[str, tuple[str, ...]] = {}
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
        actual_indexes = inspector.get_indexes(table_name)
        unique_columns = {
            tuple(item["column_names"])
            for item in [*inspector.get_unique_constraints(table_name), *actual_indexes]
            if item.get("unique", True)
        }
        missing = tuple(sorted(
            constraint.name or ",".join(col.name for col in constraint.columns)
            for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
            and tuple(col.name for col in constraint.columns) not in unique_columns
        ))
        index_names = {item["name"] for item in actual_indexes}
        missing += tuple(sorted(index.name for index in table.indexes if index.unique and index.name not in index_names))
        if missing:
            missing_unique[table_name] = missing
        missing_index = tuple(sorted(index.name for index in table.indexes if not index.unique and index.name not in index_names))
        if missing_index:
            missing_indexes[table_name] = missing_index
    missing_legacy = tuple(sorted(LEGACY_REQUIREMENTS - actual_tables))
    legacy_columns = {col["name"] for col in inspector.get_columns("articles")} if "articles" in actual_tables else set()
    missing_legacy_columns = tuple(sorted(set(Article.__table__.columns.keys()) - legacy_columns))
    applied: tuple[str, ...] = ()
    if "int_schema_version" in actual_tables:
        with engine.connect() as conn:
            applied = tuple(sorted(conn.execute(text("SELECT version_num FROM int_schema_version")).scalars()))
    revision_matches = applied == (SCHEMA_REVISION,)
    ready = not (missing_legacy or missing_tables or missing_columns or missing_unique or missing_legacy_columns)
    ready = ready and (revision_matches or not require_revision)
    return SchemaInspection(
        revision=SCHEMA_REVISION,
        dialect=engine.dialect.name,
        ready=ready,
        missing_legacy_tables=missing_legacy,
        missing_tables=tuple(missing_tables),
        unexpected_intelligence_tables=tuple(unexpected_tables),
        missing_columns=missing_columns,
        unexpected_columns=unexpected_columns,
        applied_revisions=applied,
        revision_matches=revision_matches,
        missing_unique_constraints=missing_unique,
        missing_indexes=missing_indexes,
        missing_legacy_columns=missing_legacy_columns,
    )


def readonly_inspection_engine(database_url: str) -> Engine:
    """SQLite inspection must neither create a missing file nor mutate its schema."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        if not url.database or url.database == ":memory:":
            raise ValueError("Inspection needs an existing database file")
        target = Path(url.database).expanduser().resolve(strict=True)
        if not target.is_file():
            raise ValueError("Inspection needs an existing database file")
        url = URL.create("sqlite+pysqlite", database=f"file:{target}", query={"mode": "ro", "uri": "true"})
        return create_engine(url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("Versioned intelligence storage supports SQLite and PostgreSQL")
    return create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})


def render_upgrade(dialect_name: str, *, from_revision: str = "base") -> str:
    """Compile frozen Alembic revisions without loading config, secrets or any DB."""
    from alembic import command
    from alembic.config import Config

    if dialect_name not in {"sqlite", "postgresql"}:
        raise ValueError("versioned migrations support sqlite or postgresql")
    if from_revision not in {"base", BASELINE_REVISION, SCHEMA_REVISION}:
        raise ValueError("unknown source revision")
    output = StringIO()
    config = Config(output_buffer=output)
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "migrations/intelligence"))
    config.set_main_option("intelligence.dialect", dialect_name)
    command.upgrade(config, f"{from_revision}:{SCHEMA_REVISION}", sql=True)
    return (
        "-- CANDIDATE ONLY / NOT EXECUTED. Review the AI-DB handoff before use.\n"
        "-- Step 1: read-only precheck and approve exact source revision/target/recovery.\n"
        "-- Step 2: human/DBA only; includes schema DDL and revision-metadata DML.\n"
        "-- <++>\n" + output.getvalue() + "-- <++>\n"
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
