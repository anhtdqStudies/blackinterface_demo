"""Projects: named DataServer connections and their frozen snapshots.

Follows the repository shape set by `meta.py`: takes a `Database`, speaks SQL,
returns plain Python. The snapshot payload is an opaque JSON string here — the
store layer does not know what a StationObs is; (de)serialization happens in
the caller (api layer), keeping this package free of domain imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import Row

from blackinterface.store.db import Database


@dataclass(frozen=True)
class ProjectRow:
    id: int
    name: str
    opcua_url: str
    created_at: str
    updated_at: str
    # From the latest snapshot, if any. Enough for a project list; the payload
    # itself is fetched separately because it can be hundreds of KB.
    has_snapshot: bool
    model_name: str | None
    model_version: str | None
    captured_at: str | None
    snapshot_saved_at: str | None


_LIST_SQL = """
SELECT p.id, p.name, p.opcua_url, p.created_at, p.updated_at,
       s.project_id IS NOT NULL AS has_snapshot,
       s.model_name, s.model_version, s.captured_at,
       s.saved_at AS snapshot_saved_at
FROM projects p
LEFT JOIN project_snapshots s ON s.project_id = p.id
"""


def _row(row: Row) -> ProjectRow:
    return ProjectRow(
        id=int(row["id"]),
        name=str(row["name"]),
        opcua_url=str(row["opcua_url"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        has_snapshot=bool(row["has_snapshot"]),
        model_name=row["model_name"],
        model_version=row["model_version"],
        captured_at=row["captured_at"],
        snapshot_saved_at=row["snapshot_saved_at"],
    )


class ProjectRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, name: str, opcua_url: str) -> ProjectRow:
        now = datetime.now(UTC).isoformat()
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO projects (name, opcua_url, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (name, opcua_url, now, now),
            )
            project_id = cursor.lastrowid
        assert project_id is not None
        found = self.get(project_id)
        assert found is not None
        return found

    def get(self, project_id: int) -> ProjectRow | None:
        row = self.db.connection.execute(_LIST_SQL + " WHERE p.id = ?", (project_id,)).fetchone()
        return _row(row) if row else None

    def get_by_name(self, name: str) -> ProjectRow | None:
        row = self.db.connection.execute(_LIST_SQL + " WHERE p.name = ?", (name,)).fetchone()
        return _row(row) if row else None

    def list(self) -> list[ProjectRow]:
        rows = self.db.connection.execute(_LIST_SQL + " ORDER BY p.name").fetchall()
        return [_row(r) for r in rows]

    def delete(self, project_id: int) -> bool:
        """Deletes the project and (via FK cascade) its snapshot."""
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cursor.rowcount > 0

    # -------------------------------------------------------------- snapshots
    def save_snapshot(
        self,
        project_id: int,
        obs_json: str,
        *,
        model_name: str = "",
        model_version: str | None = None,
        captured_at: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO project_snapshots "
                "(project_id, obs_json, model_name, model_version, captured_at, saved_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(project_id) DO UPDATE SET "
                "obs_json = excluded.obs_json, model_name = excluded.model_name, "
                "model_version = excluded.model_version, "
                "captured_at = excluded.captured_at, saved_at = excluded.saved_at",
                (project_id, obs_json, model_name, model_version, captured_at, now),
            )
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))

    def load_snapshot(self, project_id: int) -> str | None:
        row = self.db.connection.execute(
            "SELECT obs_json FROM project_snapshots WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return str(row["obs_json"]) if row else None
