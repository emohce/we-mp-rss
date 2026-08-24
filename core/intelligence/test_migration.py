from __future__ import annotations

import unittest

from sqlalchemy import create_engine, inspect

from core.models.article import Article
from core.models.base import Base

from .migration import inspect_schema, intelligence_tables, render_ddl


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


if __name__ == "__main__":
    unittest.main()
