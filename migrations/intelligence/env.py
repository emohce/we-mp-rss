"""Offline Alembic environment: never opens an application database."""
from alembic import context

if not context.is_offline_mode():
    raise RuntimeError("This environment is render-only. Give reviewed SQL to the DBA.")

context.configure(
    dialect_name=context.config.get_main_option("intelligence.dialect"),
    literal_binds=True,
    version_table="int_schema_version",
    transactional_ddl=True,
)
with context.begin_transaction():
    context.run_migrations()
