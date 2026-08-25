"""`/api/summary`: one scope, one answer, and the evidence behind it.

This is the first facet that carries an `EvidenceRecord`, so the tests here are
as much about the envelope as about the answer. What they hold:

  * a scope is resolved or refused, never widened (ADR-0010)
  * the answer only covers what the scope covers
  * the caveats are derived, not remembered by whoever wrote the facet
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from blackinterface.api import app as app_module
from blackinterface.api import deps
from blackinterface.api.source import StationStore
from blackinterface.api.summary import build_summary
from blackinterface.config import Settings
from blackinterface.domain.evidence import LimitCode
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE


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


@pytest.fixture
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("summary")
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


# --------------------------------------------------------------------- scope
async def test_a_bay_summary_covers_that_bay_and_no_more(store: StationStore) -> None:
    out = build_summary(store, "bay:D03")
    assert out.scope == "bay:D03"
    assert out.bays == ["D03"]
    assert sum(out.switch_states.values()) == len(store.graph.devices_of("D03"))
    assert {r.subject for r in out.measurements} == {"bay:D03"}


async def test_a_station_summary_reaches_every_bay(store: StationStore) -> None:
    out = build_summary(store, "station")
    assert len(out.bays) == len(store.graph.bays)
    subjects = {r.subject for r in out.measurements}
    assert any(s.startswith("busbar:") for s in subjects)
    assert any(s.startswith("transformer:") for s in subjects)


async def test_a_voltage_level_does_not_borrow_the_other_levels_busbars(
    store: StationStore,
) -> None:
    out = build_summary(store, "vl:220kV")
    assert out.bays and all(store.graph.bay(b).voltage_level == "220kV" for b in out.bays)
    for reading in out.measurements:
        if reading.subject.startswith("busbar:"):
            busbar_id = reading.subject.removeprefix("busbar:")
            found = next(b for b in store.graph.busbars if b.id == busbar_id)
            assert found.voltage_level == "220kV"


async def test_a_transformer_scope_answers_about_both_of_its_bays(
    store: StationStore,
) -> None:
    """`transformer:AT1` covers the 220kV and the 110kV bay it couples — the
    pairing the graph already established from their display names."""
    out = build_summary(store, "transformer:AT1")
    assert len(out.bays) >= 2
    assert len({store.graph.bay(b).voltage_level for b in out.bays}) >= 2


async def test_an_unknown_scope_is_refused_not_widened(store: StationStore) -> None:
    """The failure mode this guards against: a question about one bay quietly
    answered about the whole station."""
    from blackinterface.errors import InvalidInputError, NotFoundError

    with pytest.raises(NotFoundError):
        build_summary(store, "bay:NOPE")
    with pytest.raises(InvalidInputError):
        build_summary(store, "feeder:D03")


# ------------------------------------------------------------------ evidence
async def test_the_evidence_names_every_point_the_answer_rests_on(
    store: StationStore,
) -> None:
    out = build_summary(store, "bay:D03")
    points = {q.point for q in out.evidence.quality}
    assert points, "an answer with no points behind it is not evidence"
    assert all(p.startswith("point:D03.") for p in points)
    assert out.evidence.coverage.resolved == len(out.evidence.quality)
    assert out.evidence.subject == "bay:D03"
    assert out.evidence.tool == "summary"


async def test_an_unmeasured_scale_is_declared_rather_than_printed(
    store: StationStore,
) -> None:
    """The DataServer publishes no engineering units, so most numbers arrive
    with `unit="?"`. That has to reach the operator as a caveat, not be papered
    over with a plausible-looking kV."""
    out = build_summary(store, "bay:D03")
    codes = {limit.code for limit in out.evidence.limits}
    assert LimitCode.UNIT_UNVERIFIED in codes
    unverified = next(x for x in out.evidence.limits if x.code is LimitCode.UNIT_UNVERIFIED)
    assert unverified.count == sum(1 for r in out.measurements if r.unit == "?")


async def test_a_switch_that_has_not_moved_is_not_called_stale(store: StationStore) -> None:
    """Found by running it (2026-08-06): every device position carried a
    day-old `SourceTimestamp`, because that is when it last *moved*. Ageing
    them flagged 89 of 159 points on a perfectly healthy station — a caveat
    that always fires teaches the operator to ignore the evidence block, which
    is precisely what the block exists to prevent."""
    out = build_summary(store, "station")
    positions = [q for q in out.evidence.quality if q.point.endswith(".PosSt")]
    old = [q for q in positions if q.age_ms and q.age_ms > 60_000]
    assert old, "the fixture must contain positions older than the threshold"
    # The age is still reported — it is worth showing, just not a fault.
    assert all(q.age_ms is not None for q in old)

    stale = [x for x in out.evidence.limits if x.code is LimitCode.DATA_STALE]
    flagged = {subject for limit in stale for subject in limit.subjects}
    assert not any(s.endswith(".PosSt") for s in flagged)
    # The fixture's analog values *are* genuinely old, and those are supposed to
    # keep arriving — so the caveat still has something to say.
    assert flagged, "a stale measurement must still be reported"


async def test_a_deadbanded_answer_says_it_was_deadbanded(store: StationStore) -> None:
    """ADR-0012 consequence 3: a filter the operator cannot see is a filter
    they cannot judge."""
    out = build_summary(store, "bay:D03")
    assert LimitCode.DEADBAND_APPLIED in {limit.code for limit in out.evidence.limits}


async def test_a_fixture_is_reported_as_a_fixture(store: StationStore) -> None:
    out = build_summary(store, "station")
    assert out.evidence.source.kind == "fixture"
    assert out.evidence.model_version == store.graph.model_version


# ----------------------------------------------------------------- endpoint
def test_the_endpoint_defaults_to_the_whole_station(client: TestClient) -> None:
    body = client.get("/api/summary").json()
    assert body["scope"] == "station"
    assert body["kind"] == "station"
    assert body["evidence"]["tool"] == "summary"


def test_the_endpoint_refuses_a_scope_it_cannot_parse(client: TestClient) -> None:
    assert client.get("/api/summary", params={"scope": "bay:"}).status_code == 400
    assert client.get("/api/summary", params={"scope": "bay:GHOST"}).status_code == 404


def test_the_endpoint_answers_for_one_bay(client: TestClient) -> None:
    body = client.get("/api/summary", params={"scope": "bay:D03"}).json()
    assert body["bays"] == ["D03"]
    assert body["label"]
    assert body["measurements"]
    assert body["evidence"]["coverage"]["requested"] >= len(body["measurements"])
