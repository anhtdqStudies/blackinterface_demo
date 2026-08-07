"""The measurement throttle: slow the announcements, never lose the last one.

The failure this guards against is subtle. A leading-edge-only throttle drops
everything inside the window, so the *last* reading of a burst — the current
value — never reaches the client, which is then left showing a stale number
with nothing saying it is stale. The trailing edge is what makes it converge.
"""

from __future__ import annotations

import asyncio

from blackinterface.api.throttle import Throttle


async def test_the_first_offer_fires_at_once() -> None:
    """No latency added to a station that was quiet — the throttle exists to
    cap a burst, not to delay the first news of one."""
    fired = _Counter()
    throttle = Throttle(0.05, fired)
    throttle.offer()
    assert fired.count == 1
    throttle.cancel()


async def test_a_burst_fires_once_now_and_once_at_the_end() -> None:
    fired = _Counter()
    throttle = Throttle(0.05, fired)
    for _ in range(20):
        throttle.offer()
    assert fired.count == 1
    await asyncio.sleep(0.12)
    assert fired.count == 2, "the last reading of the burst must still arrive"
    throttle.cancel()


async def test_a_quiet_window_costs_nothing() -> None:
    """No offers inside the window means no trailing edge — an idle station
    must not generate traffic."""
    fired = _Counter()
    throttle = Throttle(0.02, fired)
    throttle.offer()
    await asyncio.sleep(0.1)
    assert fired.count == 1
    throttle.cancel()


async def test_cancelling_forgets_the_pending_edge() -> None:
    """Used when the model is unloaded: an announcement about a station we no
    longer hold would be about nothing."""
    fired = _Counter()
    throttle = Throttle(0.05, fired)
    throttle.offer()
    throttle.offer()
    assert throttle.pending
    throttle.cancel()
    await asyncio.sleep(0.1)
    assert fired.count == 1


async def test_a_zero_interval_is_a_pass_through() -> None:
    """What tests configure, so they need no clock at all."""
    fired = _Counter()
    throttle = Throttle(0.0, fired)
    throttle.offer()
    throttle.offer()
    assert fired.count == 2


class _Counter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1
