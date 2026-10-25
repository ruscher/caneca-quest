"""Database engine, sessions, migrations and backups."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.url = f"sqlite:///{path}"
        self.engine: Engine = create_engine(self.url, connect_args={"check_same_thread": False})
        event.listen(self.engine, "connect", _sqlite_pragmas)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """A unit of work: commits on success, rolls back on any error."""
        session = self._sessions()
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    # -- migrations ----------------------------------------------------------------
    def _alembic_config(self) -> Config:
        cfg = Config()
        cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        cfg.set_main_option("sqlalchemy.url", self.url)
        cfg.attributes["engine"] = self.engine
        return cfg

    def current_revision(self) -> str | None:
        with self.engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()

    def head_revision(self) -> str | None:
        return ScriptDirectory.from_config(self._alembic_config()).get_current_head()

    def migrate(self, backup_dir: Path | None = None, keep: int = 5) -> None:
        current, head = self.current_revision(), self.head_revision()
        if current == head:
            return
        if current is not None and backup_dir is not None:
            self.backup(backup_dir, keep, reason=f"pre-migration-{current}")
        log.info("migrating database %s -> %s", current, head)
        command.upgrade(self._alembic_config(), "head")

    # -- backups -------------------------------------------------------------------
    def backup(self, backup_dir: Path, keep: int = 5, reason: str = "manual") -> Path:
        """Consistent online copy using SQLite's backup API (safe while in use)."""
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        target = backup_dir / f"caneca-{stamp}-{reason}.db"
        src = sqlite3.connect(self.path)
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        backups = sorted(backup_dir.glob("caneca-*.db"))
        for old in backups[:-keep] if keep > 0 else []:
            old.unlink(missing_ok=True)
        return target

    def list_backups(self, backup_dir: Path) -> list[Path]:
        return sorted(backup_dir.glob("caneca-*.db"), reverse=True)

    def dispose(self) -> None:
        self.engine.dispose()
