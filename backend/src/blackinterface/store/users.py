"""Accounts, their roles, and their sessions (ADR-0016 section 7, ADR-0017).

Same shape as `projects.py`: takes a `Database`, speaks SQL, returns plain
Python. It stores role *names* as strings and never imports `domain.authz` —
the store layer holds no opinion about what a role grants, which is what keeps
the permission model in one place instead of two.

Hashing is not done here either; the caller hands over a hash. `store/` decides
where bytes live, `passwords.py` decides what they are.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from sqlite3 import Row

from blackinterface.store.db import Database


@dataclass(frozen=True)
class UserRow:
    id: int
    username: str
    display_name: str
    password_hash: str | None
    external_id: str | None
    created_at: str
    password_changed_at: str | None
    disabled_at: str | None
    roles: tuple[str, ...] = field(default=())

    @property
    def enabled(self) -> bool:
        return self.disabled_at is None

    @property
    def uses_seeded_password(self) -> bool:
        """Never changed since the install seeded it. Worth saying out loud."""
        return self.password_hash is not None and self.password_changed_at is None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row(row: Row, roles: tuple[str, ...]) -> UserRow:
    return UserRow(
        id=int(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        password_hash=row["password_hash"],
        external_id=row["external_id"],
        created_at=str(row["created_at"]),
        password_changed_at=row["password_changed_at"],
        disabled_at=row["disabled_at"],
        roles=roles,
    )


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------ users
    def create(
        self,
        username: str,
        display_name: str,
        *,
        password_hash: str | None,
        roles: Sequence[str],
        external_id: str | None = None,
    ) -> UserRow:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, external_id, "
                "created_at) VALUES (?, ?, ?, ?, ?)",
                (username, display_name, password_hash, external_id, _now()),
            )
            user_id = cursor.lastrowid
            assert user_id is not None
            conn.executemany(
                "INSERT OR IGNORE INTO user_roles (user_id, role) VALUES (?, ?)",
                [(user_id, role) for role in roles],
            )
        found = self.get(user_id)
        assert found is not None
        return found

    def get(self, user_id: int) -> UserRow | None:
        row = self.db.connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row(row, self._roles(user_id)) if row else None

    def get_by_username(self, username: str) -> UserRow | None:
        row = self.db.connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return _row(row, self._roles(int(row["id"]))) if row else None

    def list(self) -> list[UserRow]:
        rows = self.db.connection.execute("SELECT * FROM users ORDER BY username").fetchall()
        return [_row(r, self._roles(int(r["id"]))) for r in rows]

    def count(self) -> int:
        row = self.db.connection.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return int(row["n"])

    def set_password(self, user_id: int, password_hash: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?",
                (password_hash, _now(), user_id),
            )

    def set_roles(self, user_id: int, roles: Sequence[str]) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
            conn.executemany(
                "INSERT INTO user_roles (user_id, role) VALUES (?, ?)",
                [(user_id, role) for role in roles],
            )

    def set_disabled(self, user_id: int, disabled: bool) -> None:
        """Disabling also drops the sessions — otherwise the account keeps
        working until its cookie expires, which is not what "disable" means."""
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET disabled_at = ? WHERE id = ?",
                (_now() if disabled else None, user_id),
            )
            if disabled:
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def _roles(self, user_id: int) -> tuple[str, ...]:
        rows = self.db.connection.execute(
            "SELECT role FROM user_roles WHERE user_id = ? ORDER BY role", (user_id,)
        ).fetchall()
        return tuple(str(r["role"]) for r in rows)

    # --------------------------------------------------------------- sessions
    def start_session(self, user_id: int, token_hash: str, *, ttl_hours: float) -> str:
        now = datetime.now(UTC)
        expires = now + timedelta(hours=ttl_hours)
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions "
                "(token_hash, user_id, created_at, expires_at, last_seen) VALUES (?, ?, ?, ?, ?)",
                (token_hash, user_id, now.isoformat(), expires.isoformat(), now.isoformat()),
            )
        return expires.isoformat()

    def user_for_session(self, token_hash: str) -> UserRow | None:
        """The signed-in user, or None if the token is unknown, expired, or the
        account has since been disabled.

        Expiry is compared here rather than swept on a timer: a session that has
        run out must stop working at the moment it runs out, not at the next
        sweep. `purge_expired()` only reclaims space.
        """
        row = self.db.connection.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(str(row["expires_at"])) <= datetime.now(UTC):
            return None
        user = self.get(int(row["user_id"]))
        return user if user is not None and user.enabled else None

    def touch_session(self, token_hash: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET last_seen = ? WHERE token_hash = ?", (_now(), token_hash)
            )

    def end_session(self, token_hash: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def purge_expired(self) -> int:
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now(),))
        return cursor.rowcount
