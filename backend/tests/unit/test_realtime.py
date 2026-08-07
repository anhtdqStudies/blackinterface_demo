"""Realtime: from a pushed reading to a recoloured diagram.

The chain under test, end to end and offline:

    OPC UA notification -> PointSample -> apply_state_samples(StationObs)
      -> build_station -> solve_energization -> /api/live -> SSE event

No DataServer is contacted anywhere in this module. The notification is
injected where asyncua would have delivered it, and everything downstream is
the real code path — which is the only way to know that a switch moving in the
substation actually changes what an operator sees.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest
from asyncua import ua
from fastapi.testclient import TestClient

from blackinterface.api import app as app_module
from blackinterface.api import deps
from blackinterface.api.broadcast import Cadence
from blackinterface.api.routers.live import live_events
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.energization import LiveState, solve_energization
from blackinterface.domain.models import PointSample, Quality, SwitchState
from blackinterface.domain.observation import (
    StationObs,
    apply_state_samples,
    measurement_points,
    state_points,
    watch_points,
)
from blackinterface.domain.topology import build_station
from blackinterface.integration.opcua.monitor import (
    MonitorStatus,
    StationMonitor,
    _Handler,
    _Inbox,
)
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE

# The two points every test below leans on, chosen because their behaviour is
# documented in docs/40-testing/manual-test-01-topology.md.
D01_BREAKER = "ns=2;s=D01.XCBR1.PosSt"
BB21_LIVE = "ns=2;s=BB21.IsLive"


def _ref(obs: StationObs, bay_id: str, ln: str) -> str:
    bay = next(b for b in obs.bays if b.id == bay_id)
    ref = next(n for n in bay.logical_nodes if n.ln == ln).position.source_ref
    assert ref is not None
    return ref


def _busbar_ref(obs: StationObs, busbar_id: str) -> str:
    ref = next(b for b in obs.busbars if b.id == busbar_id).is_live.source_ref
    assert ref is not None
    return ref


def _closed(value: object) -> PointSample:
    return PointSample(value=value, quality=Quality.GOOD)


# ------------------------------------------------------- what can be watched
def test_state_points_are_the_positions_and_the_live_flags(observation: StationObs) -> None:
    """Only what moves. Names and the tree shape are not subscribed to — if
    those changed, the station would need browsing again, not patching."""
    points = state_points(observation)
    assert points == tuple(sorted(points)), "must be deterministic, order included"
    assert len(points) == len(set(points))
    assert _ref(observation, "D01", "XCBR1") in points
    assert _busbar_ref(observation, "BB21") in points
    assert all(p.endswith((".PosSt", ".IsLive")) for p in points)


def test_the_two_cadences_never_share_a_point(observation: StationObs) -> None:
    """ADR-0012 rule 1 at its root. A point in both lists would be routed to
    both handlers, and an analog value would end up rebuilding the graph — the
    exact thing the split exists to prevent."""
    state = set(state_points(observation))
    measured = set(measurement_points(observation))
    assert state and measured
    assert not (state & measured)
    assert set(watch_points(observation)) == state | measured


def test_a_point_with_no_address_is_not_watchable(observation: StationObs) -> None:
    """A logical node the DataServer never bound has nothing to subscribe to,
    and inventing an address for it would subscribe to the wrong node."""
    blind = [
        ln.ln
        for bay in observation.bays
        for ln in bay.logical_nodes
        if ln.position.source_ref is None
    ]
    points = watch_points(observation)
    assert all(not any(p.endswith(f".{ln}.PosSt") for p in points) for ln in blind)


# ------------------------------------------------------------ applying a batch
def test_a_batch_about_another_station_changes_nothing(observation: StationObs) -> None:
    """Identity, not just equality: the caller uses it to skip the rebuild."""
    patched = apply_state_samples(observation, {"ns=2;s=SOMEWHERE.ELSE.PosSt": _closed(1)})
    assert patched is observation
    assert apply_state_samples(observation, {}) is observation


def test_a_new_position_reaches_the_graph(observation: StationObs) -> None:
    ref = _ref(observation, "D01", "XCBR1")
    assert build_station(observation).device("D01.XCBR1").state is SwitchState.CLOSED

    patched = apply_state_samples(observation, {ref: _closed(1)})  # Dbpos 1 = OPEN
    device = build_station(patched).device("D01.XCBR1")
    assert device is not None
    assert device.state is SwitchState.OPEN
    # Everything else stayed put — a batch patches points, not the station.
    assert len(build_station(patched).devices) == len(build_station(observation).devices)


def test_the_patched_point_keeps_its_own_address(observation: StationObs) -> None:
    """A notification carries a value, not an identity. Taking the incoming
    source_ref would let a mis-routed sample rewrite where a point came from,
    and the provenance trail (I6) is the thing that has to stay true."""
    ref = _ref(observation, "D01", "XCBR1")
    patched = apply_state_samples(observation, {ref: PointSample(value=1, quality=Quality.GOOD)})
    device = build_station(patched).device("D01.XCBR1")
    assert device is not None
    assert device.position.source_ref == ref


def test_an_unreadable_position_arriving_live_degrades_to_undetermined(
    observation: StationObs,
) -> None:
    """Doubt must survive the trip (I2). A BAD notification is not a position."""
    ref = _ref(observation, "D01", "XCBR1")
    patched = apply_state_samples(observation, {ref: PointSample(value=2, quality=Quality.BAD)})
    device = build_station(patched).device("D01.XCBR1")
    assert device is not None
    assert device.state is SwitchState.UNDETERMINED


def test_a_busbar_going_dead_reaches_the_colouring(observation: StationObs) -> None:
    """The whole point of realtime, in one assertion: a single pushed reading
    changes what the 220kV busbar is drawn as."""
    before = solve_energization(build_station(observation))
    assert before.state_of("NODE.BB21") is LiveState.LIVE

    dead = {
        _busbar_ref(observation, "BB21"): _closed(False),
        _busbar_ref(observation, "BB22"): _closed(False),
    }
    after = solve_energization(build_station(apply_state_samples(observation, dead)))
    assert after.state_of("NODE.BB21") is LiveState.DEAD


# -------------------------------------------------------------- the inbox
def test_two_readings_of_one_point_coalesce_to_the_newer() -> None:
    """Within one window they are two readings of the same thing, and only the
    newer one is the position now. Redrawing the older would be a lie."""
    inbox = _Inbox()
    inbox.put("A", _closed(2))
    inbox.put("A", _closed(1))
    inbox.put("B", _closed(2))
    batch = inbox.drain()
    assert batch["A"].value == 1
    assert set(batch) == {"A", "B"}


def test_draining_leaves_the_inbox_empty_and_unarmed() -> None:
    inbox = _Inbox()
    inbox.put("A", _closed(2))
    assert inbox.ready.is_set()
    inbox.drain()
    assert not inbox.ready.is_set()
    assert inbox.drain() == {}


def test_the_handler_carries_quality_through_untouched() -> None:
    """A notification the server marks bad must arrive marked bad."""
    inbox = _Inbox()
    handler = _Handler(inbox)

    class FakeNode:
        nodeid = ua.NodeId.from_string(D01_BREAKER)

    class FakeNotification:
        monitored_item = ua.MonitoredItemNotification(
            Value=ua.DataValue(
                ua.Variant(None),
                StatusCode=ua.StatusCode(ua.StatusCodes.BadWaitingForInitialData),
            )
        )

    handler.datachange_notification(FakeNode(), None, FakeNotification())
    sample = inbox.drain()[D01_BREAKER]
    assert sample.quality is Quality.BAD
    assert sample.source_ref == D01_BREAKER


# ------------------------------------------------------------ the supervisor
async def test_a_link_that_will_not_come_up_is_reported_not_raised() -> None:
    """An unreachable DataServer is a state to display, not a crash. The
    supervisor must keep retrying and keep saying it is not connected."""
    attempts = 0

    async def failing_session(self: StationMonitor) -> None:
        nonlocal attempts
        attempts += 1
        raise OSError("connection refused")

    monitor = StationMonitor("opc.tcp://nowhere:1", ["ns=2;s=X"], on_batch=_ignore)
    monitor._session = failing_session.__get__(monitor)  # type: ignore[method-assign]
    await monitor.start()
    await _until(lambda: attempts >= 1)
    try:
        assert monitor.status.connected is False
        assert monitor.status.error is not None
        assert "connection refused" in monitor.status.error
    finally:
        await monitor.stop()
    assert monitor.status.connected is False


async def test_stopping_a_monitor_that_never_started_is_harmless() -> None:
    monitor = StationMonitor("opc.tcp://nowhere:1", [], on_batch=_ignore)
    await monitor.stop()
    await monitor.start()
    await monitor.stop()
    await monitor.stop()


def test_a_degraded_link_is_one_the_operator_should_be_told_about() -> None:
    assert MonitorStatus(connected=True, watching=10).degraded is False
    assert MonitorStatus(connected=False).degraded is True
    # Connected, but part of the station is not being watched — the screen is
    # current in some places and frozen in others, which is worse than either.
    assert MonitorStatus(connected=True, watching=10, rejected=1).degraded is True


async def _ignore(batch: dict[str, PointSample]) -> None:
    return None


async def _until(predicate: Any, timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition never held")
        await asyncio.sleep(0.01)


# ------------------------------------------------------------------- the store
@pytest.fixture
async def store(tmp_path: Path) -> StationStore:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    database = Database(tmp_path / "test.sqlite")
    database.migrate()
    made = StationStore(
        Settings(source="fixture", fixture=SAS_TREE, data_dir=tmp_path, realtime=False),
        database,
    )
    await made.startup()
    return made


async def test_a_pushed_reading_changes_the_model_and_the_revision(
    store: StationStore,
) -> None:
    before = store.state_revision
    structure = store.structure_revision
    assert store.graph.device("D01.XCBR1").state is SwitchState.CLOSED

    await store.apply_live({D01_BREAKER: _closed(1)})

    assert store.graph.device("D01.XCBR1").state is SwitchState.OPEN
    assert store.state_revision > before
    assert store.structure_revision == structure, "no re-browse, so no new geometry"


async def test_a_reading_that_matches_nothing_is_not_announced(store: StationStore) -> None:
    """A stale NodeId must not make every client redraw for no reason."""
    before = store.state_revision
    await store.apply_live({"ns=2;s=GONE.PosSt": _closed(1)})
    assert store.state_revision == before


async def test_listeners_are_woken_and_then_forgotten(store: StationStore) -> None:
    async with store.listen() as listener:
        await store.apply_live({D01_BREAKER: _closed(1)})
        assert await listener.take(timeout=1) == (Cadence.STATE,)
    assert not store._broadcast.listeners, "leaving the block must unsubscribe"


async def test_a_slow_listener_loses_intermediate_revisions_not_the_latest(
    store: StationStore,
) -> None:
    """One slot per cadence on purpose: a client renders the present, so
    falling behind should cost it history, never currency."""
    async with store.listen() as listener:
        await store.apply_live({D01_BREAKER: _closed(1)})
        await store.apply_live({D01_BREAKER: _closed(2)})
        assert listener.pending == {Cadence.STATE}
    assert store.graph.device("D01.XCBR1").state is SwitchState.CLOSED


# ----------------------------------------------------------------- the wiring
# Everything above tests the pieces. These test that they are connected: that
# opening a project actually opens a subscription, pointed at that project's
# DataServer, delivering into that store.


class _FakeMonitor:
    """Stands in for StationMonitor so the wiring can be tested with no server."""

    log: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, url: str, points: Any, **kwargs: Any) -> None:
        self.url = url
        self.points = tuple(points)
        self.on_batch = kwargs["on_batch"]
        self.on_status = kwargs.get("on_status")

    async def start(self) -> None:
        _FakeMonitor.log.append(("start", self.url))

    async def stop(self) -> None:
        _FakeMonitor.log.append(("stop", self.url))


@pytest.fixture
def fake_monitor(monkeypatch: pytest.MonkeyPatch) -> type[_FakeMonitor]:
    from blackinterface.integration.opcua import monitor as monitor_module

    _FakeMonitor.log = []
    monkeypatch.setattr(monitor_module, "StationMonitor", _FakeMonitor)
    return _FakeMonitor


def _watching_store(tmp_path: Path) -> StationStore:
    database = Database(tmp_path / "test.sqlite")
    database.migrate()
    made = StationStore(
        Settings(source="fixture", fixture=SAS_TREE, data_dir=tmp_path, realtime=True),
        database,
    )

    async def observe(url: str) -> StationObs:
        from blackinterface.integration.dump import load_dump

        return load_dump(SAS_TREE).model_copy(update={"source": url})

    made._observe_opcua = observe  # type: ignore[method-assign]
    return made


async def test_opening_a_project_starts_watching_its_own_dataserver(
    tmp_path: Path, fake_monitor: type[_FakeMonitor], observation: StationObs
) -> None:
    store = _watching_store(tmp_path)
    row = store.projects.create("Trạm A", "opc.tcp://10.0.0.5:48050")
    await store.refresh_project(row.id)

    assert fake_monitor.log == [("start", "opc.tcp://10.0.0.5:48050")]
    watcher = store._watch.monitor
    assert watcher.points == watch_points(observation)

    # And the callback it was handed is really this store's, so a notification
    # arriving from asyncua lands in the model an operator is looking at.
    await watcher.on_batch({D01_BREAKER: _closed(1)})
    assert store.graph.device("D01.XCBR1").state is SwitchState.OPEN
    await store.shutdown()


async def test_a_snapshot_is_watched_too_so_it_stops_being_a_snapshot(
    tmp_path: Path, fake_monitor: type[_FakeMonitor]
) -> None:
    """Opening offline renders instantly from the stored structure; the
    subscription then corrects every reading in it."""
    store = _watching_store(tmp_path)
    row = store.projects.create("Trạm A", "opc.tcp://10.0.0.5:48050")
    await store.refresh_project(row.id)
    fake_monitor.log = []

    await store.open_project(row.id)
    assert store.graph.source.startswith("snapshot:")
    # Same URL and same points, so the existing link is kept rather than torn
    # down and rebuilt for nothing.
    assert fake_monitor.log == []
    assert store._watch.monitor is not None
    await store.shutdown()


async def test_a_fixture_is_never_watched(tmp_path: Path, fake_monitor: type[_FakeMonitor]) -> None:
    store = _watching_store(tmp_path)
    await store.startup()
    assert store.loaded
    assert store._watch.monitor is None
    assert store.monitor_status is None
    assert fake_monitor.log == []


async def test_deleting_the_project_lets_go_of_its_dataserver(
    tmp_path: Path, fake_monitor: type[_FakeMonitor]
) -> None:
    store = _watching_store(tmp_path)
    row = store.projects.create("Trạm A", "opc.tcp://10.0.0.5:48050")
    await store.refresh_project(row.id)
    await store.unload()
    assert fake_monitor.log[-1] == ("stop", "opc.tcp://10.0.0.5:48050")
    assert store._watch.monitor is None


# --------------------------------------------------------------- the endpoints
@pytest.fixture
def served(store: StationStore) -> Iterator[StationStore]:
    """Make `store` the one the endpoint module reads, and put back what was
    there — the module-level store is shared with the other API tests."""
    original = deps.get_store()
    deps.use(store)
    try:
        yield store
    finally:
        deps.use(original)


@pytest.fixture
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("live")
    database = Database(data_dir / "test.sqlite")
    deps.use(
        StationStore(
            Settings(source="fixture", fixture=SAS_TREE, data_dir=data_dir, realtime=False),
            database,
        ),
        database,
    )
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_the_live_document_covers_every_drawn_device(client: TestClient) -> None:
    """The join the UI performs: a symbol without a live entry would keep
    rendering its position from the moment the drawing was made."""
    state = client.get("/api/live").json()["state"]
    diagram = client.get("/api/diagram").json()
    assert state["loaded"] is True
    for symbol in diagram["symbols"]:
        assert symbol["device_id"] in state["devices"], symbol["device_id"]
    assert state["energization"]["summary"]["mismatched"] == 0
    assert set(state["bay_is_live"]) == {b["id"] for b in client.get("/api/bays").json()}


def test_an_unreadable_is_live_is_published_as_null_not_false(client: TestClient) -> None:
    """`false` is a claim that the bay is dead. Only a GOOD reading may make
    it (I2) — everything else is an absence, and must look like one."""
    state = client.get("/api/live").json()["state"]
    for bay in client.get("/api/bays").json():
        if bay["is_live_quality"] != "GOOD":
            assert state["bay_is_live"][bay["id"]] is None, bay["id"]


def test_a_source_with_no_server_behind_it_says_so(client: TestClient) -> None:
    """A fixture cannot be subscribed to. Claiming otherwise would put a
    reassuring green dot over a screen that will never update."""
    link = client.get("/api/live").json()["link"]
    assert link["realtime"] is False
    assert link["connected"] is False


def test_the_measurements_arrive_with_the_first_poll(client: TestClient) -> None:
    """A number the operator can read is part of the present tense, not an
    extra request they have to know to make."""
    measurement = client.get("/api/live").json()["measurement"]
    assert measurement["readings"]["bay:D03"], "D03 carries an MMXU1"
    reading = next(r for r in measurement["readings"]["bay:D03"] if r["measurand"] == "MMXU1.Hz")
    assert reading["unit"] == "Hz"
    assert reading["quality"] == "GOOD"
    assert isinstance(reading["value"], float)


def test_the_stream_route_is_a_readable_event_stream(client: TestClient) -> None:
    """Only the framing: the endpoint's body is `live_events`, driven directly
    in the two tests below. Iterating an endless stream through TestClient
    would hang rather than fail, which is a worse test than none."""
    schema = client.get("/openapi.json").json()["paths"]["/api/stream"]["get"]
    assert "text/event-stream" in schema["responses"]["200"]["content"]


async def test_the_stream_opens_with_every_cadence(served: StationStore) -> None:
    """No separate initial fetch: connecting is enough to know where you are —
    and that means all three cadences, not just the one that moves most."""
    store = served
    events = live_events()
    try:
        opening = [_parse(await anext(events)) for _ in range(3)]
    finally:
        await events.aclose()

    assert [cadence for cadence, _ in opening] == ["state", "measurement", "link"]
    state = dict(opening)["state"]
    assert state["loaded"] is True
    assert state["revision"] == store.state_revision
    assert state["devices"]["D01.XCBR1"]["state"] == "CLOSED"


async def test_the_stream_pushes_the_new_state_when_a_switch_moves(
    served: StationStore,
) -> None:
    """The assertion realtime exists for."""
    store = served
    events = live_events()
    try:
        first = dict([_parse(await anext(events)) for _ in range(3)])["state"]
        await store.apply_live({D01_BREAKER: _closed(1)})
        cadence, second = _parse(await asyncio.wait_for(anext(events), timeout=2))
    finally:
        await events.aclose()

    assert cadence == "state", "a position moving is not a measurement"
    assert first["devices"]["D01.XCBR1"]["state"] == "CLOSED"
    assert second["devices"]["D01.XCBR1"]["state"] == "OPEN"
    assert second["revision"] > first["revision"]
    # Geometry did not move, so a client keeps the drawing it already has.
    assert second["structure_revision"] == first["structure_revision"]


def _parse(chunk: str) -> tuple[str, Any]:
    head, _, body = chunk.partition("\n")
    assert head.startswith("event: ")
    return head.removeprefix("event: "), json.loads(body.removeprefix("data: ").strip())
