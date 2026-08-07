"""Turning a source into a `StationObs`. The one place `api/` does I/O to read.

The importers are imported *inside* the methods that need them, not at module
level. That is deliberate and enforced: `api` must not pull `asyncua` into its
import graph, and `tests/unit/test_architecture.py` checks exactly that (I6).

Failures are translated here into `SourceUnavailableError`, so callers never
have to know whether the thing that went wrong was a socket, a certificate or a
missing file — only that the station could not be read, and from where.
"""

from __future__ import annotations

from blackinterface.config import Settings
from blackinterface.domain.observation import StationObs
from blackinterface.errors import SourceUnavailableError
from blackinterface.logs import get_logger

log = get_logger(__name__)


class SourceReader:
    """Reads a station observation from wherever the settings point."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def from_settings(self) -> StationObs:
        """The BI_SOURCE fallback: used when no project is active."""
        if self._settings.source == "opcua":
            return await self.from_opcua(self._settings.opcua_url)
        return self.from_fixture()

    async def from_opcua(self, url: str) -> StationObs:
        # Lazy: keeps asyncua out of the api import graph (AGENTS.md I6).
        from blackinterface.integration.opcua.discovery import discover_station

        if not self._settings.opcua_user:
            log.warning(
                "connecting to OneATS anonymously - a real station must use a "
                "read-only account (AGENTS.md I1)",
                url=url,
            )
        try:
            return await discover_station(
                url,
                username=self._settings.opcua_user,
                password=self._settings.opcua_password,
                timeout=self._settings.opcua_timeout,
            )
        except Exception as exc:
            raise SourceUnavailableError(
                f"cannot read the OneATS DataServer: {exc}",
                url=url,
            ) from exc

    def from_fixture(self) -> StationObs:
        from blackinterface.integration.dump import load_dump

        path = self._settings.fixture
        if not path.exists():
            raise SourceUnavailableError(
                f"fixture not found: {path}. Generate it with: "
                "python tools/probe_dataserver.py --dump --slim --depth 4 "
                "--out backend/tests/fixtures/sas_tree.json",
                path=str(path),
            )
        return load_dump(path)
