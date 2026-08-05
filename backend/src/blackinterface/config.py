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
