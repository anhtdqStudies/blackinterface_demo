"""Where the language model is configured, and where its key lives.

The one row in `assistant_config` overrides `BI_LLM*`. That direction is
deliberate: the environment is how a developer or a CI run pins a model, and the
database is how the station's engineer sets one — the station's answer should
win over the machine's default, not the other way round.

**The key leaves this module only as far as `agent/provider.py`.** Nothing in
`api/` reads it, and no response body carries it; `AssistantConfigOut` says
whether one is present and never what it is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from blackinterface.store.db import Database
from blackinterface.store.secrets import seal, unseal


@dataclass(frozen=True)
class AssistantConfig:
    """What the station chose. `api_key` is decrypted and must not be logged."""

    provider: str = "off"
    base_url: str = ""
    model: str = ""
    api_key: str | None = None
    timeout: float = 120.0
    #: When the settings were last proved to reach a real model, or None. A key
    #: that has never answered is not the same as a key that works.
    verified_at: str | None = None
    updated_at: str = ""
    updated_by: str = ""

    @property
    def configured(self) -> bool:
        return self.provider != "off" and bool(self.model)

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)


class AssistantRepository:
    def __init__(self, db: Database, secret: str) -> None:
        self.db = db
        self._secret = secret

    def get(self) -> AssistantConfig | None:
        """The stored configuration, or None when nobody has set one."""
        row = self.db.connection.execute(
            "SELECT provider, base_url, model, api_key_enc, timeout, verified_at, "
            "updated_at, updated_by FROM assistant_config WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return AssistantConfig(
            provider=str(row["provider"]),
            base_url=str(row["base_url"]),
            model=str(row["model"]),
            api_key=unseal(row["api_key_enc"], self._secret),
            timeout=float(row["timeout"]),
            verified_at=row["verified_at"],
            updated_at=str(row["updated_at"]),
            updated_by=str(row["updated_by"]),
        )

    def save(
        self,
        *,
        provider: str,
        base_url: str,
        model: str,
        timeout: float,
        actor: str,
        api_key: str | None,
        keep_key: bool,
    ) -> AssistantConfig:
        """Write the configuration.

        `keep_key` is how the settings screen saves a change of model without
        being sent the key back. A form that had to round-trip the secret to
        keep it would mean the API answering with it, which is the one thing
        this module exists to avoid.

        Any save clears `verified_at`: the previous proof was about the previous
        settings, and carrying it forward would show a green tick for an
        endpoint nobody has ever reached.
        """
        now = datetime.now(UTC).isoformat()
        with self.db.transaction() as conn:
            if keep_key:
                conn.execute(
                    "INSERT INTO assistant_config "
                    "(id, provider, base_url, model, timeout, verified_at, updated_at, updated_by)"
                    " VALUES (1, ?, ?, ?, ?, NULL, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET provider = excluded.provider, "
                    "base_url = excluded.base_url, model = excluded.model, "
                    "timeout = excluded.timeout, verified_at = NULL, "
                    "updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                    (provider, base_url, model, timeout, now, actor),
                )
            else:
                conn.execute(
                    "INSERT INTO assistant_config "
                    "(id, provider, base_url, model, api_key_enc, timeout, verified_at, "
                    "updated_at, updated_by) VALUES (1, ?, ?, ?, ?, ?, NULL, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET provider = excluded.provider, "
                    "base_url = excluded.base_url, model = excluded.model, "
                    "api_key_enc = excluded.api_key_enc, timeout = excluded.timeout, "
                    "verified_at = NULL, updated_at = excluded.updated_at, "
                    "updated_by = excluded.updated_by",
                    (
                        provider,
                        base_url,
                        model,
                        seal(api_key, self._secret) if api_key else None,
                        timeout,
                        now,
                        actor,
                    ),
                )
        # Read back rather than returning what was passed in: the caller then
        # sees the key as it decrypts, which is the round trip that actually
        # matters when BI_SECRET_KEY is wrong.
        stored = self.get()
        if stored is None:  # pragma: no cover - written in the transaction above
            raise RuntimeError("assistant_config vanished immediately after being written")
        return stored

    def mark_verified(self) -> None:
        """Record that these exact settings reached a model and it answered."""
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE assistant_config SET verified_at = ? WHERE id = 1",
                (datetime.now(UTC).isoformat(),),
            )
