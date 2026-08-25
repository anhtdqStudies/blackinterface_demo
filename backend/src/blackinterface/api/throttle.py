"""Rate-limiting an announcement without ever losing the last one.

Analog readings arrive as fast as the DataServer publishes them. Waking every
open stream that often is waste, but simply dropping announcements inside the
window is wrong in a specific way: the *last* reading of a burst is the current
value, and a client that never hears about it is left showing a stale number
with no indication that it is stale.

So this is a trailing-edge throttle. The first offer fires immediately; offers
inside the cooldown are remembered, and one more announcement fires when the
cooldown ends. The client therefore always converges on the present, at a rate
we choose.

Only measurements use this (ADR-0012 rule 2). Positions are never throttled — a
breaker that trips and recloses inside the window is exactly what must be seen.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable


class Throttle:
    """Fire at most once per `interval`, and always once after the last offer."""

    def __init__(self, interval_seconds: float, fire: Callable[[], None]) -> None:
        self._interval = max(0.0, interval_seconds)
        self._fire = fire
        self._handle: asyncio.TimerHandle | None = None
        self._deferred = False

    @property
    def pending(self) -> bool:
        """Whether an announcement is waiting for the cooldown to end."""
        return self._deferred

    def offer(self) -> None:
        """Ask for an announcement. Called from the event loop's thread."""
        if self._interval <= 0:
            self._fire()
            return
        if self._handle is not None:
            self._deferred = True  # inside the cooldown: fold into the trailing edge
            return
        self._fire()
        self._arm()

    def cancel(self) -> None:
        """Forget any pending trailing edge. Used when the model is unloaded."""
        if self._handle is not None:
            self._handle.cancel()
            self._handle = None
        self._deferred = False

    # ------------------------------------------------------------------ humble
    def _arm(self) -> None:
        self._handle = asyncio.get_running_loop().call_later(self._interval, self._elapsed)

    def _elapsed(self) -> None:
        self._handle = None
        if not self._deferred:
            return
        self._deferred = False
        self._fire()
        self._arm()  # a burst keeps the window open until it truly stops
