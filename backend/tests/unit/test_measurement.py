"""Measurements: the catalog, the deadband, and the boundary they must not cross.

The tests that matter most here are not about numbers. They are about the two
rules that keep analog data from doing damage (ADR-0012):

  * a measurement never changes the electrical graph, and
  * a unit is never printed unless it was measured.

Everything runs offline from the committed dump.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.energization import solve_energization
from blackinterface.domain.measurement import (
    ALL_MEASURANDS,
    BAY_MEASURANDS,
    BUSBAR_MEASURANDS,
    TRANSFORMER_MEASURANDS,
    Measurand,
    Quantity,
    Unit,
    filter_deadband,
    read_measurements,
    significant,
)
from blackinterface.domain.models import PointSample, Quality
from blackinterface.domain.observation import (
    StationObs,
    apply_measurement_samples,
    measurement_points,
)
from blackinterface.domain.scope import ScopeRef
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE

D03_TOTW = "MMXU1.totW"


def _good(value: float) -> PointSample:
    return PointSample(value=value, quality=Quality.GOOD)


# ------------------------------------------------------------------- catalog
def test_every_measurand_is_readable_from_the_committed_dump(observation: StationObs) -> None:
    """The catalog and the fixture have to stay in step: a measurand nothing
    reads is a line of dead configuration that looks like coverage."""
    readings = read_measurements(observation)
    found = {r.measurand.key for r in readings.readings}
    assert found >= {m.key for m in BAY_MEASURANDS}
    assert found >= {m.key for m in BUSBAR_MEASURANDS}
    assert found >= {m.key for m in TRANSFORMER_MEASURANDS}


def test_a_unit_is_only_printed_when_the_scale_was_measured() -> None:
    """The DataServer publishes no EngineeringUnits. So `Vlin` reads 221.08 and
    we do not know whether that is volts or kilovolts — printing either would be
    inventing a fact. Only quantities that cannot be mis-scaled carry a unit."""
    by_key = {m.key: m for m in ALL_MEASURANDS}
    assert by_key["MMXU1.Hz"].unit is Unit.HERTZ
    assert by_key["MMXU1.totPF"].unit is Unit.NONE
    assert by_key["YLTC.TapPos"].unit is Unit.STEP
    for key in ("MMXU1.totW", "MMXU1.totVAr", "MMXU1.Vlin", "MMXU1.Amax", "PPVmax"):
        assert by_key[key].unit is Unit.UNKNOWN, key


def test_a_reading_that_is_not_good_has_no_number(observation: StationObs) -> None:
    """Same rule as a switch position (I2): doubt is not a value."""
    readings = read_measurements(observation)
    reading = readings.of(ScopeRef.bay("D03"))[0]
    bad = reading.model_copy(update={"sample": PointSample(value=1.0, quality=Quality.BAD)})
    assert reading.number is not None
    assert bad.number is None
    assert bad.sample.value == 1.0, "the raw value stays, for provenance"


def test_readings_are_addressed_in_the_scope_vocabulary(observation: StationObs) -> None:
    readings = read_measurements(observation)
    reading = next(r for r in readings.readings if r.subject == ScopeRef.bay("D03"))
    assert reading.id.startswith("bay:D03/")
    assert reading.point.ref.startswith("point:D03.")


def test_a_subject_only_appears_when_it_actually_measures(observation: StationObs) -> None:
    """A bay with no instrument transformers has no readings — not empty ones.
    Absent and unreadable are different facts (I2)."""
    readings = read_measurements(observation)
    measuring = {s.ref for s in readings.subjects()}
    assert "bay:D03" in measuring
    assert len(measuring) < len(observation.bays) + len(observation.busbars)


# ------------------------------------------------------------------ deadband
_POWER = Measurand(ln="MMXU1", da="totW", quantity=Quantity.ACTIVE_POWER, deadband_pct=0.5)
_FREQ = Measurand(
    ln="MMXU1", da="Hz", quantity=Quantity.FREQUENCY, unit=Unit.HERTZ, deadband_abs=0.01
)


def test_a_small_move_is_dropped_and_a_real_one_is_not() -> None:
    assert not significant(_good(100.0), _good(100.2), _POWER)
    assert significant(_good(100.0), _good(101.0), _POWER)


def test_frequency_is_judged_absolutely_because_a_percentage_would_hide_it() -> None:
    """0.5 % of 50 Hz is 0.25 Hz — an excursion an operator must see. One
    global percentage cannot serve both power and frequency."""
    assert significant(_good(50.00), _good(50.02), _FREQ)
    assert not significant(_good(50.000), _good(50.005), _FREQ)


def test_quality_is_never_deadbanded() -> None:
    """A point going bad is news whatever the number does — and a point coming
    back is news too, even if it returns to the value it had."""
    bad = PointSample(value=100.0, quality=Quality.BAD)
    assert significant(_good(100.0), bad, _POWER)
    assert significant(bad, _good(100.0), _POWER)
    assert not significant(bad, PointSample(value=100.0, quality=Quality.BAD), _POWER)


def test_tap_position_has_no_deadband_at_all() -> None:
    """It is discrete, like a switch position. Smoothing it would hide the tap
    operation an operator is watching for."""
    tap = TRANSFORMER_MEASURANDS[0]
    assert tap.deadband_pct == 0.0
    assert tap.deadband_abs == 0.0
    assert significant(_good(10), _good(11), tap)


def test_an_override_replaces_the_percentage_but_not_the_floor() -> None:
    assert not significant(_good(100.0), _good(101.0), _POWER, pct_override=5.0)
    assert significant(_good(100.0), _good(106.0), _POWER, pct_override=5.0)


def test_filtering_leaves_points_it_does_not_recognise_alone(observation: StationObs) -> None:
    """This function quietens known analog points. Swallowing an unknown ref
    would hide a routing mistake instead of surfacing it."""
    stranger = {"ns=2;s=NOT.A.MEASURAND": _good(1.0)}
    assert filter_deadband(observation, stranger) == stranger


def test_filtering_drops_the_noise_and_keeps_the_move(observation: StationObs) -> None:
    ref = _totw_ref(observation, "D03")
    current = _current(observation, ref)
    assert current is not None
    noise = {ref: _good(current * 1.0001)}
    move = {ref: _good(current * 1.5 + 1.0)}
    assert filter_deadband(observation, noise) == {}
    assert filter_deadband(observation, move) == move


# ---------------------------------------------------- the boundary (ADR-0012)
def test_applying_a_measurement_cannot_move_a_switch(observation: StationObs) -> None:
    """The pure half of rule 1: the measurement patcher touches measurands and
    nothing else, so no caller of it can change a position."""
    ref = _totw_ref(observation, "D03")
    patched = apply_measurement_samples(observation, {ref: _good(999.0)})
    assert patched is not observation
    assert [b.logical_nodes[0].position for b in patched.bays] == [
        b.logical_nodes[0].position for b in observation.bays
    ]
    assert [b.is_live for b in patched.busbars] == [b.is_live for b in observation.busbars]


@pytest.fixture
async def store(tmp_path: Path) -> StationStore:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    database = Database(tmp_path / "test.sqlite")
    database.migrate()
    made = StationStore(
        Settings(
            source="fixture",
            fixture=SAS_TREE,
            data_dir=tmp_path,
            realtime=False,
            measurement_throttle_ms=0,
        ),
        database,
    )
    await made.startup()
    return made


async def test_a_measurement_batch_leaves_the_station_exactly_as_it_was(
    store: StationStore,
) -> None:
    """The rule this whole split exists to enforce. A load moving must not
    rebuild the graph, must not re-solve energisation, and must not make a
    client redraw — otherwise a storm of analog values delays the one thing
    that is safety-critical, a breaker that tripped."""
    graph_before = store.graph
    energised_before = solve_energization(graph_before)
    structure_before = store.structure_revision
    state_before = store.state_revision
    measured_before = store.measurement_revision

    ref = _totw_ref(store._obs, "D03")
    await store.apply_live({ref: _good(_current(store._obs, ref) * 2 + 50)})

    assert store.graph is graph_before, "the graph object itself must not be rebuilt"
    assert solve_energization(store.graph) == energised_before
    assert store.structure_revision == structure_before
    assert store.state_revision == state_before
    assert store.measurement_revision > measured_before


async def test_a_measurement_inside_the_deadband_announces_nothing(
    store: StationStore,
) -> None:
    before = store.measurement_revision
    ref = _totw_ref(store._obs, "D03")
    await store.apply_live({ref: _good(_current(store._obs, ref) * 1.0001)})
    assert store.measurement_revision == before


async def test_one_batch_can_carry_both_cadences(store: StationStore) -> None:
    """The subscription does not sort its notifications; the store does."""
    state_before = store.state_revision
    measured_before = store.measurement_revision
    ref = _totw_ref(store._obs, "D03")
    await store.apply_live(
        {
            "ns=2;s=D01.XCBR1.PosSt": PointSample(value=1, quality=Quality.GOOD),
            ref: _good(_current(store._obs, ref) * 2 + 50),
        }
    )
    assert store.state_revision > state_before
    assert store.measurement_revision > measured_before


async def test_a_reading_reaches_the_measurement_set(store: StationStore) -> None:
    ref = _totw_ref(store._obs, "D03")
    await store.apply_live({ref: _good(123456.0)})
    reading = next(
        r for r in store.measurements.of(ScopeRef.bay("D03")) if r.measurand.key == D03_TOTW
    )
    assert reading.number == 123456.0


# -------------------------------------------------------------------- helpers
def _totw_ref(obs: StationObs, bay_id: str) -> str:
    bay = next(b for b in obs.bays if b.id == bay_id)
    ln = next(n for n in bay.logical_nodes if n.ln == "MMXU1")
    ref = next(m for m in ln.measurands if m.da == "totW").sample.source_ref
    assert ref is not None
    assert ref in measurement_points(obs)
    return ref


def _current(obs: StationObs, source_ref: str) -> float:
    for bay in obs.bays:
        for ln in bay.logical_nodes:
            for measurand in ln.measurands:
                if measurand.sample.source_ref == source_ref:
                    return float(measurand.sample.value)  # type: ignore[arg-type]
    raise AssertionError(f"no such measurand: {source_ref}")


def test_a_stale_reading_is_still_good_quality() -> None:
    """A reminder in test form, because it trips people up: GOOD says the value
    arrived intact, not that it is current. Age is judged separately, by
    `domain/evidence.py`."""
    old = PointSample(
        value=1.0,
        quality=Quality.GOOD,
        source_timestamp=datetime.now(UTC) - timedelta(hours=2),
    )
    assert old.usable
