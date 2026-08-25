"""Keeping the alarm subscription alive and folding what it says into the store.

The counterpart to `watch.py`, which does the same job for point values. Kept
separate because the two channels fail independently: a station whose alarm
subscription has dropped is still worth drawing, and vice versa.

`sync()` is idempotent for the same reason it is there — it is called after
every model install, and in most of those cases the subscription already running
is the one wanted. Restarting it anyway would drop and re-establish a connection
to a substation for no reason.
"""

from __future__ import annotations

from typing import Any

from blackinterface.api.alarmsource import AlarmStore
from blackinterface.api.broadcast import Cadence, RevisionBroadcaster
from blackinterface.config import Settings
from blackinterface.logs import get_logger

log = get_logger(__name__)


class AlarmSupervisor:
    """Owns the alarm subscription, or owns nothing when there is none to own."""

    def __init__(
        self,
        settings: Settings,
        alarms: AlarmStore,
        broadcast: RevisionBroadcaster,
    ) -> None:
        self._settings = settings
        self._alarms = alarms
        self._broadcast = broadcast
        self._monitor: Any = None  # AlarmMonitor, typed loosely to keep asyncua out

    @property
    def monitor(self) -> Any:
        """The running monitor, or None. Exposed for diagnostics and tests."""
        return self._monitor

    async def sync(self, url: str | None) -> None:
        """Make the subscription match this url. Same target -> leave it alone."""
        if self._monitor is not None and self._monitor.url != url:
            await self.stop()
        if url is None or self._monitor is not None:
            return

        # Lazy, like every other asyncua import reachable from api/ (I6).
        from blackinterface.integration.opcua.alarm_events import AlarmMonitor

        self._monitor = AlarmMonitor(
            url,
            on_event=self._on_event,
            on_snapshot=self._on_snapshot,
            username=self._settings.opcua_user,
            password=self._settings.opcua_password,
            timeout=self._settings.opcua_timeout,
        )
        await self._monitor.start()

    async def stop(self) -> None:
        monitor, self._monitor = self._monitor, None
        if monitor is not None:
            await monitor.stop()
        # Deliberately not clearing the store: what we last heard stays on
        # screen, badged as stale. An empty alarm pane looks exactly like a
        # healthy station, which is the one thing it must never be mistaken for.

    async def _on_snapshot(self, records: list[Any]) -> None:
        from blackinterface.integration.alarm_map import from_record

        alarms = [from_record(record) for record in records]
        count = self._alarms.load_snapshot(alarms)
        log.info("alarm snapshot loaded", count=count)
        self._broadcast.bump(Cadence.ALARM)

    async def _on_event(self, fields: dict[str, Any]) -> None:
        from blackinterface.integration.alarm_map import from_event

        if self._alarms.apply_event(from_event(fields)):
            self._broadcast.bump(Cadence.ALARM)
