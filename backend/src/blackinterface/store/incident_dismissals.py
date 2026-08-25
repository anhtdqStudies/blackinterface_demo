"""Local operator dismissals for incidents — not OneATS ack (I1).

Follows the repository shape of `conversations.py`: SQL in one place, plain rows
out. The API layer joins this with live clustering in `api/alarms.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import Row

from blackinterface.store.db import Database


@dataclass(frozen=True)
class DismissalRow:
    incident_id: str
    actor: str
    dismissed_at: str
    view_scope: str
    payload: str


def _row(raw: Row) -> DismissalRow:
    return DismissalRow(
        incident_id=str(raw["incident_id"]),
        actor=str(raw["actor"]),
        dismissed_at=str(raw["dismissed_at"]),
        view_scope=str(raw["view_scope"]),
        payload=str(raw["payload"]),
    )


class IncidentDismissalRepository:
    """Who dismissed which incident, and what it looked like at the time."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def dismissed_ids(self, actor: str) -> frozenset[str]:
        if not actor:
            return frozenset()
        rows = self.db.connection.execute(
            "SELECT incident_id FROM incident_dismissals WHERE actor = ?",
            (actor,),
        ).fetchall()
        return frozenset(str(row["incident_id"]) for row in rows)

    def list_for_actor(self, actor: str) -> tuple[DismissalRow, ...]:
        if not actor:
            return ()
        rows = self.db.connection.execute(
            """
            SELECT incident_id, actor, dismissed_at, view_scope, payload
            FROM incident_dismissals
            WHERE actor = ?
            ORDER BY dismissed_at DESC
            """,
            (actor,),
        ).fetchall()
        return tuple(_row(row) for row in rows)

    def record(
        self,
        *,
        incident_id: str,
        actor: str,
        view_scope: str,
        payload: str,
    ) -> DismissalRow:
        dismissed_at = datetime.now(UTC).isoformat()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO incident_dismissals
                    (incident_id, actor, dismissed_at, view_scope, payload)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (incident_id, actor) DO UPDATE SET
                    dismissed_at = excluded.dismissed_at,
                    view_scope = excluded.view_scope,
                    payload = excluded.payload
                """,
                (incident_id, actor, dismissed_at, view_scope, payload),
            )
        return DismissalRow(
            incident_id=incident_id,
            actor=actor,
            dismissed_at=dismissed_at,
            view_scope=view_scope,
            payload=payload,
        )
