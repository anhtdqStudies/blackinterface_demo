"""Keeping exactly one subscription alive, aimed at the right points.

Discovery and monitoring are two different rhythms (see `source.py`). This
module owns the second one's lifecycle: which URL is being watched, which points,
and whether the link is up.

`sync()` is the whole interface, and it is idempotent on purpose. It is called
after every model install — reopening a project from its snapshot, refreshing it
live, reloading the fixture — and in most of those cases the right answer is
"the subscription you already have is the one you want". Restarting it anyway
would drop and re-establish a connection to a substation for no reason.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from blackinterface.config import Settings
from blackinterface.domain.models import PointSample

if TYPE_CHECKING:  # the annotation only — asyncua stays out of api/ at runtime
    from blackinterface.integration.opcua.monitor import MonitorStatus

BatchHandler = Callable[[Mapping[str, PointSample]], Awaitable[None]]
StatusHandler = Callable[["MonitorStatus"], None]


class MonitorSupervisor:
    """Owns the live subscription, or owns nothing when there is none to own."""

    def __init__(
        self,
        settings: Settings,
        *,
        on_batch: BatchHandler,
        on_status: StatusHandler,
    ) -> None:
        self._settings = settings
        self._on_batch = on_batch
        self._on_status = on_status
        self._monitor: Any = None  # StationMonitor, typed loosely to keep asyncua out
        self._status: MonitorStatus | None = None

    @property
    def monitor(self) -> Any:
        """The running monitor, or None. Exposed for diagnostics and tests."""
        return self._monitor

    @property
    def status(self) -> MonitorStatus | None:
        """None when no subscription is configured for the current source."""
        return self._status

    async def sync(self, url: str | None, points: Sequence[str]) -> None:
        """Make the subscription match this url and this point list.

        Same target as the running one -> leave it alone. Different -> stop and
        start over. Nothing to watch (a fixture, realtime off, a model with no
        readable points) -> make sure nothing is running.
        """
        watched = tuple(points)
        if self._monitor is not None and (
            self._monitor.url != url or self._monitor.points != watched
        ):
            await self.stop()
        if url is None or not watched or self._monitor is not None:
            return

        # Lazy, like every other asyncua import reachable from api/ (I6).
        from blackinterface.integration.opcua.monitor import StationMonitor

        self._monitor = StationMonitor(
            url,
            watched,
            on_batch=self._on_batch,
            on_status=self._record_status,
            username=self._settings.opcua_user,
            password=self._settings.opcua_password,
            timeout=self._settings.opcua_timeout,
            publish_ms=self._settings.opcua_publish_ms,
        )
        await self._monitor.start()

    async def stop(self) -> None:
        """Release the subscription. Safe to call when there is none."""
        monitor, self._monitor = self._monitor, None
        self._status = None
        if monitor is not None:
            await monitor.stop()

    def _record_status(self, status: MonitorStatus) -> None:
        """The link coming up or going down is itself something to redraw for:
        the header says whether what you are looking at is current."""
        self._status = status
        self._on_status(status)
