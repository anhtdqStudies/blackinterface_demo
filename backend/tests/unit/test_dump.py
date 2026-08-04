"""The dump reader: the offline half of the importer pair."""

from __future__ import annotations

from typing import Any

from blackinterface.domain.models import Quality
from blackinterface.domain.observation import StationObs
from blackinterface.integration.dump import parse_dump


def test_meta_pins_the_model_version(observation: StationObs) -> None:
    """A snapshot with no ModelVersion cannot be pinned to a release (I7)."""
    assert observation.name == "DEMO_SAS"
    assert observation.model_version == "654"
    assert observation.captured_at is not None


def test_bays_and_busbars_are_found(observation: StationObs) -> None:
    assert {b.id for b in observation.bays} == {
        "D01",
        "D03",
        "D04",
        "D12",
        "D17",
        "DBB",
        "E01",
        "E02",
        "E04",
        "E05",
        "E07",
        "EBB",
        "J01",
    }
    assert {b.id for b in observation.busbars} == {"BB11", "BB12", "BB19", "BB21", "BB22", "BB29"}


def test_bare_list_still_parses() -> None:
    """Older dumps had no meta envelope; the reader must not break on them."""
    obs = parse_dump([{"path": "/SAS/220kV/D03", "nodeid": "ns=2;s=D03", "class": "Object"}])
    assert [b.id for b in obs.bays] == ["D03"]


def test_read_error_never_becomes_a_good_value() -> None:
    """`<err ...>` in a dump means the read failed - it is not a position (I2)."""
    records: list[dict[str, Any]] = [
        {"path": "/SAS/220kV/D03", "nodeid": "ns=2;s=D03", "class": "Object"},
        {"path": "/SAS/220kV/D03/XCBR1", "nodeid": "ns=2;s=D03.XCBR1", "class": "Object"},
        {
            "path": "/SAS/220kV/D03/XCBR1/PosSt",
            "nodeid": "ns=2;s=D03.XCBR1.PosSt",
            "class": "Variable",
            "value": "<err BadWaitingForInitialData>",
            "quality": "Good",
        },
    ]
    device = parse_dump(records).bays[0].logical_nodes[0]
    assert device.position.value is None
    assert device.position.quality is Quality.BAD
