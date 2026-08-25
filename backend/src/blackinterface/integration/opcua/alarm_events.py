"""The live alarm channel: an OPC UA Alarms & Conditions subscription.

Measured 2026-08-13 (ADR-0026): OneATS derives `OAAlarmType` (`ns=2;i=1101`)
from the standard `AlarmConditionType`, and a subscription filtered on that type
delivers 29 populated fields — `ActiveState`, `Retain`, `Value`, `ConditionName`,
`Severity`, `AckedState` — where the default `BaseEventType` filter delivers 13.

Two details this module exists to encode, both measured and both non-obvious:

* Only the **Server** object may be subscribed to. `OAAlarm` and `Objects` both
  report `EventNotifier = 0` and reject the subscription outright.
* OneATS replays **nothing** on subscribe and does not implement
  `ConditionRefresh` (`BadNoMatch`), so the initial active set has to be fetched
  separately. That is what `snapshot()` does.

READ-ONLY throughout (I1): browse, subscribe, and one method call that reads.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from asyncua import Client

from blackinterface.integration.opcua.alarms import decode_alarm_body, get_active_alarms
from blackinterface.integration.opcua.discovery import _find_station_root
from blackinterface.logs import get_logger

log = get_logger(__name__)

#: The OneATS alarm condition type. Every alarm event derives from it, so one
#: filter covers Discrete, Binary, Limit and RateOfChange alike.
OA_ALARM_TYPE = "ns=2;i=1101"

#: How long to wait before reconnecting after the link drops.
RECONNECT_SECONDS = 5.0

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]
SnapshotHandler = Callable[[list[Any]], Awaitable[None]]


@dataclass(slots=True)
class AlarmMonitorStatus:
    connected: bool = False
    events_received: int = 0
    snapshot_size: int = 0
    last_error: str = ""


class _Handler:
    """asyncua calls this from the client's own task; keep it non-blocking."""

    def __init__(self, monitor: AlarmMonitor) -> None:
        self._monitor = monitor

    def event_notification(self, event: Any) -> None:
        self._monitor._offer(event)

    def status_change_notification(self, status: Any) -> None:  # pragma: no cover
        log.debug("alarm subscription status", status=str(status))


class AlarmMonitor:
    """Owns one alarm subscription for its whole life, and reconnects it.

    Mirrors `StationMonitor`: `start()` returns as soon as the background task
    exists rather than waiting for the DataServer, so a station that is briefly
    unreachable never blocks the UI from rendering what it already knows.
    """

    def __init__(
        self,
        url: str,
        *,
        on_event: EventHandler,
        on_snapshot: SnapshotHandler,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
        publish_ms: float = 200.0,
    ) -> None:
        self.url = url
        self._on_event = on_event
        self._on_snapshot = on_snapshot
        self._username = username
        self._password = password
        self._timeout = timeout
        self._publish_ms = publish_ms

        self._task: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=2000)
        self._status = AlarmMonitorStatus()

    @property
    def status(self) -> AlarmMonitorStatus:
        return self._status

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._supervise(), name=f"alarms:{self.url}")
        log.info("alarm monitor starting", url=self.url)

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            # The task is being torn down; whatever it was in the middle of is
            # no longer interesting, including how it failed.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self._status.connected = False

    # ------------------------------------------------------------- internals

    def _offer(self, event: Any) -> None:
        """Flatten the event into a plain dict and hand it to the drain task.

        Flattened here rather than downstream because `asyncua`'s event object is
        a dynamically-built type; letting it past this module would put an
        `asyncua` import in `api/` and break I6.
        """
        fields: dict[str, Any] = {}
        for name in dir(event):
            if name.startswith("_") or name in ("server_handle", "internal_properties"):
                continue
            try:
                value = getattr(event, name)
            except Exception:
                continue
            if not callable(value):
                fields[name] = value
        try:
            self._queue.put_nowait(fields)
        except asyncio.QueueFull:  # pragma: no cover - only under a real storm
            log.warning("alarm event queue full, dropping oldest")
            with contextlib.suppress(asyncio.QueueEmpty, asyncio.QueueFull):
                self._queue.get_nowait()
                self._queue.put_nowait(fields)

    async def _supervise(self) -> None:
        while True:
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._status.connected = False
                self._status.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("alarm monitor lost", url=self.url, error=str(exc))
            await asyncio.sleep(RECONNECT_SECONDS)

    async def _run_once(self) -> None:
        client = Client(url=self.url, timeout=self._timeout)
        if self._username:
            client.set_user(self._username)
        if self._password:
            client.set_password(self._password)
        await client.connect()
        try:
            self._status.connected = True
            self._status.last_error = ""
            await self._snapshot(client)

            handler = _Handler(self)
            subscription = await client.create_subscription(self._publish_ms, handler)
            # Server object only: OAAlarm and Objects report EventNotifier = 0
            # and reject this outright (measured 2026-08-13).
            await subscription.subscribe_events(
                client.nodes.server, evtypes=[client.get_node(OA_ALARM_TYPE)]
            )
            log.info("alarm subscription established", url=self.url)
            await self._drain()
        finally:
            self._status.connected = False
            await client.disconnect()

    async def _snapshot(self, client: Client) -> None:
        """Read the current active set. The only channel carrying `actor`."""
        station = await _find_station_root(client)
        batch = await get_active_alarms(client, station)
        records = []
        errors = 0
        for ext in batch:
            body = getattr(ext, "Body", None)
            if not body:
                continue
            try:
                records.append(decode_alarm_body(body))
            except Exception as exc:
                errors += 1
                log.debug("alarm body decode failed", error=str(exc))
        self._status.snapshot_size = len(records)
        if errors:
            log.warning("alarm snapshot had undecodable bodies", count=errors)
        await self._on_snapshot(records)

    async def _drain(self) -> None:
        while True:
            fields = await self._queue.get()
            self._status.events_received += 1
            await self._on_event(fields)
