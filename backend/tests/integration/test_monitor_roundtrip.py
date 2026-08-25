"""Does a position actually travel from an OPC UA server into the model?

Every other realtime test injects the notification where asyncua would have
delivered it, which proves everything except the part asyncua does. This one
closes that gap by standing up a real OPC UA server on localhost, subscribing
to it with the real `StationMonitor`, and moving the value.

It uses a server of our own precisely because it *writes*: OneATS is read-only
(AGENTS.md I1) and must never be poked to make a test pass. Nothing here talks
to a DataServer, so it runs in the ordinary gate rather than under `-m live`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from asyncua import Server, ua

from blackinterface.domain.models import PointSample, Quality
from blackinterface.integration.opcua.monitor import StationMonitor

#: High, fixed, and ours. A busy port skips rather than fails: it means
#: something else on this machine is listening, not that the code is broken.
URL = "opc.tcp://127.0.0.1:48099/blackinterface-test"
POSITION = "PosSt"


@pytest.fixture
async def server() -> AsyncIterator[tuple[Server, str]]:
    instance = Server()
    await instance.init()
    instance.set_endpoint(URL)
    namespace = await instance.register_namespace("blackinterface-test")
    bay = await instance.nodes.objects.add_object(namespace, "D01")
    position = await bay.add_variable(
        ua.NodeId("D01.XCBR1.PosSt", namespace),
        POSITION,
        2,  # Dbpos 2 = CLOSED
    )
    try:
        await instance.start()
    except OSError as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"cannot bind {URL}: {exc}")
    try:
        yield instance, position.nodeid.to_string()
    finally:
        await instance.stop()


async def test_a_position_changing_on_the_server_reaches_the_callback(
    server: tuple[Server, str],
) -> None:
    instance, ref = server
    batches: list[dict[str, PointSample]] = []

    async def on_batch(samples: dict[str, PointSample]) -> None:
        batches.append(samples)

    monitor = StationMonitor(URL, [ref], on_batch=on_batch, publish_ms=50.0)
    await monitor.start()
    try:
        # Subscribing delivers the current value straight away, which is what
        # lets a client start from the stream alone with no initial read.
        await _until(lambda: len(batches) == 1)
        assert monitor.status.connected is True
        assert monitor.status.watching == 1
        assert batches[0][ref].value == 2
        assert batches[0][ref].quality is Quality.GOOD
        assert batches[0][ref].source_ref == ref, "the sample must name its own node"

        node = instance.get_node(ua.NodeId.from_string(ref))
        await node.write_value(ua.Variant(1, ua.VariantType.Int64))  # -> OPEN
        await _until(lambda: len(batches) == 2)
        assert batches[1][ref].value == 1

        await node.write_value(ua.Variant(2, ua.VariantType.Int64))  # -> CLOSED
        await _until(lambda: len(batches) == 3)
        assert batches[2][ref].value == 2
    finally:
        await monitor.stop()

    assert monitor.status.connected is False


async def test_the_link_reports_a_point_the_server_does_not_have(
    server: tuple[Server, str],
) -> None:
    """A snapshot can outlive the model it was taken from. Watching the points
    that still exist and counting the ones that do not beats refusing to watch
    anything — but the count has to be visible, because a screen that is fresh
    in some places and frozen in others is worse than one that is plainly old.
    """
    _, ref = server
    monitor = StationMonitor(
        URL, [ref, "ns=2;s=GONE.XCBR1.PosSt"], on_batch=_ignore, publish_ms=50.0
    )
    await monitor.start()
    try:
        await _until(lambda: monitor.status.connected)
        assert monitor.status.watching == 1
        assert monitor.status.rejected == 1
        assert monitor.status.degraded is True
    finally:
        await monitor.stop()


async def _ignore(batch: dict[str, PointSample]) -> None:
    return None


async def _until(predicate: object, timeout: float = 5.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():  # type: ignore[operator]
        if loop.time() > deadline:
            raise AssertionError("condition never held")
        await asyncio.sleep(0.02)
