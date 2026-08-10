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


def _node(path: str, cls: str = "Object", **extra: Any) -> dict[str, Any]:
    return {"path": path, "nodeid": f"ns=2;s={path.rsplit('/', 1)[1]}", "class": cls, **extra}


#: T220PHOCAO v1052 in miniature, browsed 2026-08-10. Three things differ from
#: DEMO_SAS: the root is the station itself (no `SAS`), the voltage level is
#: prefixed, and each bay is wrapped in `<bay>_<label>` beside its IEDs.
NESTED_DUMP: list[dict[str, Any]] = [
    _node("/T220PCA/S220kV"),
    _node("/T220PCA/S220kV/D05_DLL1"),
    _node("/T220PCA/S220kV/D05_DLL1/D05"),
    _node("/T220PCA/S220kV/D05_DLL1/D05/XCBR1"),
    _node("/T220PCA/S220kV/D05_DLL1/D05/XCBR1/Name", "Variable", value="271", quality="Good"),
    _node("/T220PCA/S220kV/D05_DLL1/D05/XCBR1/PosSt", "Variable", value=2, quality="Good"),
    _node("/T220PCA/S220kV/D05_DLL1/D05BCU"),
    _node("/T220PCA/S220kV/D05_DLL1/D05F87L"),
    _node("/T220PCA/S220kV/DBB_Busbar"),
    _node("/T220PCA/S220kV/DBB_Busbar/DBB"),
    _node("/T220PCA/S220kV/DBB_Busbar/DBB/XSWI103"),
    _node("/T220PCA/S220kV/DBB_Busbar/DBBF87B1"),
    _node("/T220PCA/Subs/BB21"),
    _node("/T220PCA/Subs/BB21/PPVmax", "Variable", value=231.4, quality="Good"),
    _node("/T220PCA/AT1"),
    _node("/T220PCA/AT1/DT1"),
    _node("/T220PCA/AT1/DT1/YPTR"),
    _node("/T220PCA/AT1/DT1/YLTC"),
    _node("/T220PCA/AT1/DT1/YLTC/TapPos", "Variable", value=9, quality="Good"),
    _node("/T220PCA/AT1/DT1F87T1"),
    _node("/T220PCA/ACQUY"),  # a station-level group that is not a transformer
]


def test_a_wrapped_bay_is_read_at_its_own_id_and_voltage() -> None:
    """The group `D05_DLL1` is scaffolding; `D05` at 220kV is the bay."""
    obs = parse_dump(NESTED_DUMP)
    bay = next(b for b in obs.bays if b.id == "D05")
    assert bay.voltage_level == "220kV"
    assert bay.source_ref == "ns=2;s=D05"
    breaker = next(ln for ln in bay.logical_nodes if ln.ln == "XCBR1")
    assert (breaker.name, breaker.position.value) == ("271", 2)


def test_ieds_beside_a_wrapped_bay_still_reach_the_classifier() -> None:
    """`DBBF87B1` is what makes DBB a busbar protection object, one level up."""
    obs = parse_dump(NESTED_DUMP)
    assert "F87B1" in next(b for b in obs.bays if b.id == "DBB").ln_names
    assert "BCU" in next(b for b in obs.bays if b.id == "D05").ln_names


def test_a_transformer_is_found_one_level_below_the_group_that_names_it() -> None:
    """`/AT1/DT1/YLTC`, not `/AT1/YLTC`. The id must stay AT1 — bays pair on it."""
    obs = parse_dump(NESTED_DUMP)
    assert [t.id for t in obs.transformers] == ["AT1"]
    tap = next(ln for ln in obs.transformers[0].logical_nodes if ln.ln == "YLTC")
    assert next(m.sample.value for m in tap.measurands if m.da == "TapPos") == 9


def test_busbars_are_found_under_a_station_root_that_is_not_called_sas() -> None:
    obs = parse_dump(NESTED_DUMP)
    assert [b.id for b in obs.busbars] == ["BB21"]
