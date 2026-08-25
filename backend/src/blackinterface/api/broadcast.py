"""Telling every open stream that something changed — and *what* changed.

One connection carries several rhythms (ADR-0012): switch positions move
rarely and rebuild the electrical graph, analog readings move constantly and
only relabel it, the link comes and goes. They share a socket because a second
EventSource would mean a second reconnect policy and a second answer to "are we
hearing the station at all", which is a safety hazard, not a tidiness problem.

So the multiplexing happens here. Each cadence has its own revision counter,
and a listener is told which cadences are pending rather than merely that
*something* is.

Kept out of the store deliberately: "what the station is" and "who has been
told" are different concerns with different tests, and only one of them needs
an event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum


class Cadence(StrEnum):
    """A rhythm on the shared stream. The value is the SSE event name."""

    STATE = "state"
    ALARM = "alarm"
    MEASUREMENT = "measurement"
    LINK = "link"


#: Emission order when more than one cadence is pending. State first, always: a
#: breaker that moved outranks a load that drifted by half a percent. Alarm sits
#: immediately behind it and ahead of measurement, and unlike measurement it is
#: never throttled (`api/throttle.py`) — dropping a reading loses a number that
#: will be resent, dropping an alarm loses the event itself.
CADENCE_ORDER: tuple[Cadence, ...] = (
    Cadence.STATE,
    Cadence.ALARM,
    Cadence.MEASUREMENT,
    Cadence.LINK,
)


class Listener:
    """One stream's pending cadences.

    A set, not a queue. A client that cannot keep up coalesces — three state
    changes while it was busy become one "state is pending", and it then reads
    the state as it is *now*, which is what it renders anyway. What it must
    never do is lose a cadence: dropping a pending `state` because a
    `measurement` arrived behind it would mean an operator not seeing a breaker
    move because the load was busy. Holding one slot per cadence makes that
    impossible by construction.
    """

    def __init__(self) -> None:
        self._pending: set[Cadence] = set()
        self._ready = asyncio.Event()

    def offer(self, cadence: Cadence) -> None:
        self._pending.add(cadence)
        self._ready.set()

    @property
    def pending(self) -> frozenset[Cadence]:
        """What is waiting to be sent. Read-only — for diagnostics and tests."""
        return frozenset(self._pending)

    async def take(self, timeout: float) -> tuple[Cadence, ...]:
        """Wait for something to send, then drain it in emission order.

        Raises `TimeoutError` when nothing happened, which is the caller's cue
        to send a keepalive rather than to assume the station went quiet.
        """
        await asyncio.wait_for(self._ready.wait(), timeout=timeout)
        pending, self._pending = self._pending, set()
        self._ready.clear()
        return tuple(cadence for cadence in CADENCE_ORDER if cadence in pending)


class RevisionBroadcaster:
    """A revision per cadence, and the listeners waiting on them."""

    def __init__(self) -> None:
        self._revisions: dict[Cadence, int] = dict.fromkeys(Cadence, 0)
        self._listeners: set[Listener] = set()

    def revision(self, cadence: Cadence) -> int:
        return self._revisions[cadence]

    @property
    def listeners(self) -> frozenset[Listener]:
        """Who is currently subscribed. Read-only — for diagnostics and tests."""
        return frozenset(self._listeners)

    def bump(self, cadence: Cadence) -> int:
        """Announce a new revision of one cadence to everyone streaming."""
        self._revisions[cadence] += 1
        for listener in self._listeners:
            listener.offer(cadence)
        return self._revisions[cadence]

    @asynccontextmanager
    async def listen(self) -> AsyncIterator[Listener]:
        """Subscribe for as long as the block runs."""
        listener = Listener()
        self._listeners.add(listener)
        try:
            yield listener
        finally:
            self._listeners.discard(listener)
