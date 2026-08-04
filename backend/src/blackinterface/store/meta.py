"""Application key/value state.

The first repository, and the shape every later one should follow: it takes a
`Database`, speaks SQL, and returns plain Python. No SQL leaves this package.
"""

from __future__ import annotations

from datetime import UTC, datetime

from blackinterface.store.db import Database

#: Keys in use. Kept here so `app_meta` does not become a junk drawer.
LAST_MODEL_VERSION = "last_model_version"
LAST_LOADED_AT = "last_loaded_at"


class MetaRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, key: str) -> str | None:
        row = self.db.connection.execute(
            "SELECT value FROM app_meta WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row else None

    def set(self, key: str, value: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO app_meta (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (key, value, datetime.now(UTC).isoformat()),
            )

    def all(self) -> dict[str, str]:
        return {
            str(r["key"]): str(r["value"])
            for r in self.db.connection.execute("SELECT key, value FROM app_meta")
        }
