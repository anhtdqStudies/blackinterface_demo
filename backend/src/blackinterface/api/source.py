"""Where the station model comes from, and the one place it is cached.

Two sources, same downstream code path:

  BI_SOURCE=fixture   read a dumped address space from disk (default)
  BI_SOURCE=opcua     browse a live OneATS DataServer

The OPC UA importer is imported lazily inside the function that needs it. That
is deliberate: `api` must not pull `asyncua` into its import graph, and the
architecture test in tests/unit/test_architecture.py checks exactly that.
"""

from __future__ import annotations

import time
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from blackinterface.domain.models import StationGraph
from blackinterface.domain.observation import StationObs
from blackinterface.domain.topology import build_station

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_FIXTURE = REPO_ROOT / "backend" / "tests" / "fixtures" / "sas_tree.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BI_", env_file=".env", extra="ignore")

    source: str = "fixture"
    fixture: Path = DEFAULT_FIXTURE
    opcua_url: str = "opc.tcp://127.0.0.1:48050"
    opcua_user: str | None = None
    opcua_password: str | None = None


class StationStore:
    """Holds the current graph. Rebuilt only on explicit reload."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._graph: StationGraph | None = None
        self._loaded_at: float | None = None
        self._load_seconds: float | None = None

    @property
    def graph(self) -> StationGraph:
        if self._graph is None:
            raise RuntimeError("station not loaded yet - call reload() first")
        return self._graph

    @property
    def loaded(self) -> bool:
        return self._graph is not None

    @property
    def loaded_at(self) -> float | None:
        return self._loaded_at

    @property
    def load_seconds(self) -> float | None:
        return self._load_seconds

    async def reload(self) -> StationGraph:
        started = time.perf_counter()
        obs = await self._observe()
        graph = build_station(obs)
        self._graph = graph
        self._load_seconds = time.perf_counter() - started
        self._loaded_at = time.time()
        return graph

    async def _observe(self) -> StationObs:
        if self.settings.source == "opcua":
            # Lazy: keeps asyncua out of the api import graph (AGENTS.md I6).
            from blackinterface.integration.opcua.discovery import discover_station

            return await discover_station(
                self.settings.opcua_url,
                username=self.settings.opcua_user,
                password=self.settings.opcua_password,
            )

        from blackinterface.integration.dump import load_dump

        path = self.settings.fixture
        if not path.exists():
            raise FileNotFoundError(
                f"fixture not found: {path}\n"
                "Generate it with:\n"
                "  python tools/probe_dataserver.py --dump --depth 4 "
                "--out backend/tests/fixtures/sas_tree.json"
            )
        return load_dump(path)
