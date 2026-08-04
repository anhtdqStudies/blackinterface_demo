"""SQLite access: connection handling, WAL, and forward-only migrations.

Why SQLite and not a server database: this product installs on one machine at
one substation (ADR-0006). A database service is one more thing to install, one
more thing to fail at 2 a.m., and one more port on a network that already has an
unsecured OPC UA endpoint.

Concurrency model
-----------------
WAL is on, so many readers and one writer can run at once. `sqlite3` connections
are not thread-safe, so each thread gets its own; FastAPI runs sync endpoints in
a thread pool, which makes that the right granularity.

Writes are serialised by SQLite itself. `busy_timeout` makes a blocked writer
wait rather than fail immediately.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from blackinterface.errors import ConfigurationError
from blackinterface.logs import get_logger

log = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

#: Applied to every connection. `foreign_keys` is off by default in SQLite and
#: has to be re-enabled per connection, which is a classic silent data bug.
PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
)


class Database:
    """A SQLite file plus its migrations. One instance per process."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._local = threading.local()
        self._migrate_lock = threading.Lock()

    # ------------------------------------------------------------ connections
    @property
    def connection(self) -> sqlite3.Connection:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            for pragma in PRAGMAS:
                conn.execute(pragma)
            self._local.conn = conn
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Explicit transaction. Rolls back on any exception."""
        conn = self.connection
        conn.execute("BEGIN")
        try:
            yield conn
        except Exception:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")

    def close(self) -> None:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ------------------------------------------------------------- migrations
    def applied_versions(self) -> set[int]:
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchall()
        if not rows:
            return set()
        return {
            int(r["version"])
            for r in self.connection.execute("SELECT version FROM schema_migrations")
        }

    def migrate(self) -> list[int]:
        """Apply every pending migration in order. Returns what was applied.

        A migration is NOT atomic: `executescript` issues its own COMMIT, so it
        cannot run inside our transaction. Therefore **every migration must be
        idempotent** — `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT
        EXISTS`, and so on — because a crash halfway through will re-run it.
        """
        files = self._migration_files()
        with self._migrate_lock:
            done = self.applied_versions()
            applied = []
            for version, name, path in files:
                if version in done:
                    continue
                conn = self.connection
                conn.executescript(path.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT OR REPLACE INTO schema_migrations (version, name, applied_at) "
                    "VALUES (?, ?, ?)",
                    (version, name, datetime.now(UTC).isoformat()),
                )
                log.info("migration applied", version=version, name=name)
                applied.append(version)
            return applied

    @staticmethod
    def _migration_files() -> list[tuple[int, str, Path]]:
        """`001_init.sql` -> (1, "init", path). Sorted, gaps not allowed."""
        found = []
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            prefix, _, name = path.stem.partition("_")
            if not prefix.isdigit():
                raise ConfigurationError(
                    f"migration filename must start with a number: {path.name}"
                )
            found.append((int(prefix), name, path))

        versions = [v for v, _, _ in found]
        if versions != list(range(1, len(versions) + 1)):
            raise ConfigurationError(
                "migration versions must be consecutive from 1", found=versions
            )
        return found
