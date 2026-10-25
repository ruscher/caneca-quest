"""Alembic environment. The engine is injected by ``Database.migrate``."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from caneca.persistence.orm import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = config.attributes.get("engine") or create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite needs batch mode for ALTER TABLE.
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
