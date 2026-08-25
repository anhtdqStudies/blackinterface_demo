"""Keep a station's measured points flowing, without browsing it again.

READ-ONLY (AGENTS.md I1). A subscription is a read: we tell OneATS which nodes
we care about and it tells us when they change. Nothing here writes, and the
client it builds is never handed outward.

The split this module completes:

    discovery.py   browse the tree      -> what the station *is*     (rare)
    monitor.py     subscribe to points  -> what the station *is doing* (constant)

Structure barely moves during operation; positions move all the time. Browsing
~6000 nodes to learn that one disconnector opened would be absurd, so the
addresses discovery already recorded in `PointSample.source_ref` become the
subscription list — the observation says what to watch, and nothing else has to
keep a parallel registry in step with it.

Two behaviours worth knowing, because both are safety-relevant:

  * **Losing the connection is not news about the station.** When the link
    drops we stop claiming to be current (`connected=False`) and keep the last
    values as they were. We never invent a position, and we never blank one —
    an operator seeing a stale-but-labelled screen is in a better place than
    one seeing an empty diagram that looks like an open station.
  * **Notifications are coalesced, not sampled.** Every change is applied; we
    only delay the rebuild a fraction of a second so that a bay operating —
    which moves a breaker and several disconnectors within a few hundred
    milliseconds — redraws once, in a consistent state, instead of five times
    through positions that never existed together.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from asyncua import Client, ua

from blackinterface.domain.models import PointSample
from blackinterface.integration.opcua.values import to_sample
from blackinterface.logs import get_logger

log = get_logger(__name__)

#: MonitoredItems are created in batches. One service call per batch; large
#: enough that a 100-point station is a single round trip, small enough that a
#: 5000-point one does not build a message the server refuses.
SUBSCRIBE_CHUNK = 250

#: How long after the first notification of a burst we wait for the rest.
COALESCE_SECONDS = 0.2

#: Reconnect backoff, doubling from the first up to the second.
RETRY_MIN_SECONDS = 2.0
RETRY_MAX_SECONDS = 30.0

#: How often we check the link is still there while nothing is changing. A
#: quiet station and a dead connection look identical otherwise.
LIVENESS_SECONDS = 5.0

SampleBatch = dict[str, PointSample]


@dataclass(frozen=True)
class MonitorStatus:
    """What to tell the operator about the link, in one object."""

    connected: bool = False
    watching: int = 0  # points the server accepted
    rejected: int = 0  # points it refused — a stale snapshot, usually
    error: str | None = None
    since: datetime | None = None  # when the link last came up or went down

    @property
    def degraded(self) -> bool:
        return not self.connected or self.rejected > 0


@dataclass
class _Inbox:
    """Notifications arriving from asyncua's task, drained by ours."""

    samples: SampleBatch = field(default_factory=dict)
    ready: asyncio.Event = field(default_factory=asyncio.Event)

    def put(self, source_ref: str, sample: PointSample) -> None:
        # Last value wins: two notifications for one point inside a single
        # coalescing window are two readings of the same thing, and only the
        # newer one is the position now.
        self.samples[source_ref] = sample
        self.ready.set()

    def drain(self) -> SampleBatch:
        batch, self.samples = self.samples, {}
        self.ready.clear()
        return batch


class _Handler:
    """asyncua calls this from its own task; we only enqueue."""

    def __init__(self, inbox: _Inbox) -> None:
        self._inbox = inbox

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        source_ref = node.nodeid.to_string()
        self._inbox.put(source_ref, to_sample(data.monitored_item.Value, source_ref))


class StationMonitor:
    """A supervised subscription: connects, watches, reconnects, reports.

    Owns one background task for its whole life. `start()` returns as soon as
    that task exists — it does not wait for the DataServer, because a station
    that is briefly unreachable must not block the UI from rendering its
    snapshot.
    """

    def __init__(
        self,
        url: str,
        points: Sequence[str],
        *,
        on_batch: Callable[[SampleBatch], Awaitable[None]],
        on_status: Callable[[MonitorStatus], None] | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
        publish_ms: float = 500.0,
    ) -> None:
        self.url = url
        self.points = tuple(points)
        self._on_batch = on_batch
        self._on_status = on_status
        self._username = username
        self._password = password
        self._timeout = timeout
        self._publish_ms = publish_ms

        self._task: asyncio.Task[None] | None = None
        self._inbox = _Inbox()
        self._status = MonitorStatus()

    @property
    def status(self) -> MonitorStatus:
        return self._status

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._supervise(), name=f"monitor:{self.url}")
        log.info("realtime monitor starting", url=self.url, points=len(self.points))

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        self._set_status(MonitorStatus())
        log.info("realtime monitor stopped", url=self.url)

    # ------------------------------------------------------------- supervision
    def _set_status(self, status: MonitorStatus) -> None:
        self._status = status
        if self._on_status is not None:
            self._on_status(status)

    async def _supervise(self) -> None:
        """Reconnect forever. Only cancellation ends this."""
        delay = RETRY_MIN_SECONDS
        while True:
            try:
                await self._session()
                delay = RETRY_MIN_SECONDS  # a clean run resets the backoff
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                self._set_status(
                    MonitorStatus(connected=False, error=reason, since=datetime.now(UTC))
                )
                log.warning(
                    "realtime link down, retrying",
                    url=self.url,
                    error=reason,
                    retry_in=round(delay, 1),
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RETRY_MAX_SECONDS)

    async def _session(self) -> None:
        """One connected lifetime: subscribe, pump, return when the link dies."""
        client = Client(url=self.url, timeout=self._timeout)
        if self._username:
            client.set_user(self._username)
            if self._password:
                client.set_password(self._password)

        async with client:
            subscription = await client.create_subscription(self._publish_ms, _Handler(self._inbox))
            try:
                accepted, rejected = await self._subscribe_all(client, subscription)
                self._set_status(
                    MonitorStatus(
                        connected=True,
                        watching=accepted,
                        rejected=rejected,
                        since=datetime.now(UTC),
                    )
                )
                log.info(
                    "realtime link up",
                    url=self.url,
                    watching=accepted,
                    rejected=rejected,
                )
                await self._pump(client)
            finally:
                # Best effort: if the link is already gone this fails, and the
                # server drops the subscription on session timeout anyway.
                with contextlib.suppress(Exception):
                    await subscription.delete()

    async def _subscribe_all(self, client: Client, subscription: Any) -> tuple[int, int]:
        """Create MonitoredItems in batches. Returns (accepted, rejected).

        A point the server refuses is not fatal. It means this snapshot names a
        node the running model no longer has, and the honest response is to
        watch the rest and say how many were lost — not to abandon the station.
        """
        accepted = rejected = 0
        unknown: list[str] = []
        for start in range(0, len(self.points), SUBSCRIBE_CHUNK):
            chunk = self.points[start : start + SUBSCRIBE_CHUNK]
            nodes = [client.get_node(ua.NodeId.from_string(ref)) for ref in chunk]
            handles = await subscription.subscribe_data_change(nodes)
            results = handles if isinstance(handles, list) else [handles]
            for ref, handle in zip(chunk, results, strict=True):
                if isinstance(handle, ua.StatusCode):
                    rejected += 1
                    unknown.append(ref)
                else:
                    accepted += 1
        if unknown:
            log.warning(
                "points the DataServer would not monitor - the snapshot may "
                "predate the running model",
                url=self.url,
                count=len(unknown),
                sample=unknown[:5],
            )
        return accepted, rejected

    async def _pump(self, client: Client) -> None:
        """Deliver coalesced batches until the connection fails."""
        while True:
            try:
                await asyncio.wait_for(self._inbox.ready.wait(), timeout=LIVENESS_SECONDS)
            except TimeoutError:
                # Nothing changed. Prove the link is still there rather than
                # assuming silence means a quiet station.
                await client.check_connection()
                continue
            await asyncio.sleep(COALESCE_SECONDS)
            batch = self._inbox.drain()
            if batch:
                await self._on_batch(batch)
