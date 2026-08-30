from __future__ import annotations

import unittest
import ast
import tempfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect

from core.models.article import Article
from core.models.base import Base

from .migration import inspect_schema, intelligence_tables, render_ddl, render_upgrade, readonly_inspection_engine


class MigrationContractTest(unittest.TestCase):
    def test_empty_database_is_reported_without_mutation(self) -> None:
        engine = create_engine("sqlite://")
        try:
            before = set(inspect(engine).get_table_names())
            result = inspect_schema(engine)
            after = set(inspect(engine).get_table_names())
            self.assertFalse(result.ready)
            self.assertIn("articles", result.missing_legacy_tables)
            self.assertIn("int_workspaces", result.missing_tables)
            self.assertEqual(before, after)
        finally:
            engine.dispose()

    def test_fixture_schema_is_ready(self) -> None:
        engine = create_engine("sqlite://")
        try:
            Base.metadata.create_all(
                engine,
                tables=[Article.__table__, *intelligence_tables()],
            )
            result = inspect_schema(engine)
            self.assertTrue(result.ready)
            self.assertEqual(result.missing_tables, ())
            self.assertEqual(result.missing_columns, {})
        finally:
            engine.dispose()

    def test_offline_ddl_compiles_for_supported_dialects(self) -> None:
        for dialect in ("sqlite", "postgresql", "mysql"):
            ddl = render_ddl(dialect)
            self.assertIn("int_workspaces", ddl)
            self.assertIn("int_outbox_events", ddl)
            self.assertIn("CREATE INDEX", ddl)

    def test_frozen_upgrade_chain_renders_without_connection(self) -> None:
        with patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("must remain offline")):
            for dialect in ("sqlite", "postgresql"):
                full = render_upgrade(dialect)
                delta = render_upgrade(dialect, from_revision="int_v2_20260824")
                for table in intelligence_tables():
                    self.assertIn("CREATE TABLE " + table.name + " (", full)
                self.assertNotIn("CREATE TABLE int_workspaces", delta)
                self.assertIn("ADD COLUMN revision", delta)
                self.assertIn("int_schema_version", full)
                self.assertIn("uq_int_global_collector", delta)
                self.assertIn("WHERE workspace_id IS NULL", delta)
                self.assertIn("fts5" if dialect == "sqlite" else "USING gin", delta)
        versions = Path(__file__).parents[2] / "migrations/intelligence/versions"
        for file in versions.glob("*.py"):
            tree = ast.parse(file.read_text())
            imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(name.startswith("core") for name in imports), "historical revisions must be frozen")

    def test_readiness_does_not_confuse_metadata_with_applied_revision(self) -> None:
        engine = create_engine("sqlite://")
        try:
            Base.metadata.create_all(engine, tables=[Article.__table__, *intelligence_tables()])
            self.assertTrue(inspect_schema(engine).ready)
            checked = inspect_schema(engine, require_revision=True)
            self.assertFalse(checked.ready)
            self.assertFalse(checked.revision_matches)
            self.assertEqual(checked.applied_revisions, ())
        finally:
            engine.dispose()

    def test_readonly_inspector_never_creates_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                readonly_inspection_engine(f"sqlite:///{target}")
            self.assertFalse(target.exists())

    def test_startup_does_not_call_schema_compatibility_mutators(self) -> None:
        tree = ast.parse((Path(__file__).parents[1] / "db.py").read_text())
        db_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Db")
        init = next(node for node in db_class.body if isinstance(node, ast.FunctionDef) and node.name == "init")
        calls = {node.func.attr for node in ast.walk(init) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertTrue({"ensure_article_columns", "create_all", "connect", "begin"}.isdisjoint(calls))
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open" for node in ast.walk(init)))


if __name__ == "__main__":
    unittest.main()
