"""One place that knows how this installation is configured.

Every setting is a `BI_*` environment variable, optionally from a `.env` file
next to the working directory. Nothing else in the codebase reads `os.environ`
directly — if you need a knob, add it here so it shows up in one list.

`domain/` must NOT import this module: the domain layer is pure and takes its
inputs as arguments (AGENTS.md I6). The architecture test enforces that.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: <repo>/backend/src/blackinterface/config.py -> <repo>
REPO_ROOT = Path(__file__).resolve().parents[3]

SourceKind = Literal["fixture", "opcua"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BI_", env_file=".env", extra="ignore")

    # ---- where the station model comes from
    source: SourceKind = "fixture"
    fixture: Path = REPO_ROOT / "backend" / "tests" / "fixtures" / "sas_tree.json"

    # ---- OneATS DataServer (READ-ONLY, AGENTS.md I1)
    opcua_url: str = "opc.tcp://127.0.0.1:48050"
    opcua_user: str | None = None
    opcua_password: str | None = None
    opcua_timeout: float = 30.0

    # ---- realtime
    #: Hold a subscription open on the active source's measured points, so the
    #: screen follows the station instead of the last browse. Off makes every
    #: model a still photograph refreshed only by /api/reload.
    realtime: bool = True
    #: OPC UA publishing interval. The floor on how stale a position can be;
    #: the server batches its notifications into this window.
    opcua_publish_ms: float = 500.0

    # ---- measurements (ADR-0012)
    #: Override every measurand's own deadband with this percentage. Left unset
    #: on purpose: one percentage cannot serve both power and frequency, so the
    #: per-quantity defaults in `domain/measurement.py` are the sane answer and
    #: this exists only for an installation that has measured better ones.
    measurement_deadband_pct: float | None = None
    #: Slowest rate at which a measurement pulse reaches open streams. Trailing
    #: edge, so the last reading of a burst always arrives — see `throttle.py`.
    measurement_throttle_ms: float = 1000.0

    # ---- who is using this installation (ADR-0016, ADR-0017)
    #: `session` — identity comes from signing in; accounts live in SQLite.
    #: `env`     — no login at all; the whole process runs as `BI_ROLE`. For
    #:             development and for automated checks. Never at a station:
    #:             it hands the same permissions to anyone who can reach the port.
    auth: Literal["session", "env"] = "session"

    #: Only read when `auth="env"`. Comma separated, because one person holding
    #: several roles is the normal case at a lightly-manned station:
    #:     BI_ROLE=operator,maintenance
    role: str = "operator"
    user: str = "local"

    #: How long a sign-in lasts. A shift plus a margin — long enough not to
    #: interrupt handover, short enough that a forgotten browser stops working.
    session_hours: float = 12.0
    session_cookie: str = "bi_session"
    #: Set true behind HTTPS. Left false because a station install is plain HTTP
    #: on the local network today, and a Secure cookie there is simply never sent
    #: — which looks like a broken login rather than a security setting.
    cookie_secure: bool = False

    #: Create one account per role on a database that has none, so a fresh
    #: install can be signed in to. See `api/accounts.py` for the list.
    seed_accounts: bool = True
    #: The password those accounts get. Known, therefore not a secret — the app
    #: says so at startup for every account that still has it.
    seed_password: str = "blackinterface"

    # ---- local storage
    data_dir: Path = REPO_ROOT / "data"
    db_name: str = "blackinterface.sqlite"

    # ---- logging
    log_level: str = "INFO"
    log_json: bool = False  # True in production; human-readable while developing

    # ---- HTTP
    #: The Vite dev server runs on its own port and calls this API cross-origin.
    #: In production the frontend is served from the same origin and this is unused.
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name

    @property
    def frontend_dir(self) -> Path | None:
        """The built SPA, or None when it has not been built yet.

        There is deliberately no fallback UI: a stale second frontend is worse
        than none (ADR-0009). Build it with `cd frontend && npm run build`.
        """
        dist = REPO_ROOT / "frontend" / "dist"
        return dist if (dist / "index.html").exists() else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
