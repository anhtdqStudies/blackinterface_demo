"""What moves: one poll endpoint and one stream, four cadences.

`/api/live` hands over all four at once — a client that has just connected
needs the whole present tense before it can render anything. `/api/stream`
then sends each cadence separately, as its own SSE event type, whenever that
one changes (ADR-0012):

    event: state        positions, IsLive, energisation   rare, rebuilds
    event: alarm        what is annunciated                bursty, never throttled
    event: measurement  analog readings                   dense, deadbanded
    event: link         the subscription's own health     rare

One connection, one reconnect policy, one indicator. A second EventSource would
mean two answers to "are we hearing the station at all", and a station that has
gone quiet already looks exactly like a link that has died — the operator must
never have to reconcile two badges to find out which it is.

The schemas are the same in both directions, so the client applies a cadence
with the same code whether it arrived by poll or by push.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from blackinterface.api.authz import requires
from blackinterface.api.broadcast import CADENCE_ORDER, Cadence
from blackinterface.api.deps import get_alarms, get_store
from blackinterface.api.mappers import (
    alarm_live_out,
    link_out,
    live_out,
    measurement_out,
    state_out,
)
from blackinterface.api.schemas import LiveOut
from blackinterface.api.source import StationStore
from blackinterface.domain.authz import Capability

router = APIRouter()

#: Sent when nothing has changed, to keep proxies from closing an idle stream.
_HEARTBEAT_SECONDS = 20.0

#: How to render each cadence. One table, so adding a cadence is one line here
#: and one line in `Cadence` — not a new branch in the middle of the generator.
_RENDER = {
    Cadence.STATE: state_out,
    # Reads the alarm store rather than the station one: alarms are their own
    # source (ADR-0026) and deliberately not folded into the graph.
    Cadence.ALARM: lambda _store: alarm_live_out(get_alarms()),
    Cadence.MEASUREMENT: measurement_out,
    Cadence.LINK: link_out,
}


@router.get(
    "/api/live",
    response_model=LiveOut,
    dependencies=[requires(Capability.STATION_READ)],
)
async def live() -> LiveOut:
    """One poll of everything `/api/stream` pushes. The fallback when SSE cannot
    get through, and what the UI loads before the stream's first event."""
    return live_out(get_store())


async def live_events() -> AsyncIterator[str]:
    """The SSE body: the full picture, then each cadence as it changes.

    Separate from the endpoint so it can be driven directly in tests — an
    infinite generator behind a TestClient is a hang waiting to happen, and
    this is where all the behaviour worth asserting on lives anyway.
    """
    store = get_store()
    async with store.listen() as listener:
        for cadence in CADENCE_ORDER:
            yield _event(cadence, store)
        while True:
            try:
                pending = await listener.take(timeout=_HEARTBEAT_SECONDS)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            for cadence in pending:
                # Always serialise as of *now*, not as of the revision that woke
                # us: a client is entitled to the present, and coalescing here
                # costs it nothing.
                yield _event(cadence, store)


@router.get(
    "/api/stream",
    responses={200: {"content": {"text/event-stream": {}}, "description": "Live cadences"}},
    response_class=StreamingResponse,
    # Checked once, when the stream opens. A long-lived connection therefore
    # outlives a permission change — acceptable while the principal comes from
    # an environment variable, and the thing to revisit when sessions arrive.
    dependencies=[requires(Capability.STATION_READ)],
)
async def stream() -> StreamingResponse:
    """Push each cadence whenever it moves (Server-Sent Events).

    The first three events are the current state, measurements and link, so a
    client needs no separate initial fetch. Read-only in both directions: SSE
    has no channel back, and the data behind it is a subscription to OneATS,
    never a command to it (I1).
    """
    return StreamingResponse(
        live_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # nginx would otherwise sit on each event
            "Connection": "keep-alive",
        },
    )


def _event(cadence: Cadence, store: StationStore) -> str:
    payload: BaseModel = _RENDER[cadence](store)
    return f"event: {cadence.value}\ndata: {payload.model_dump_json()}\n\n"
