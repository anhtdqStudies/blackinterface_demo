"""The alarm and incident facets over HTTP, on a fixture station.

No DataServer: alarms are pushed into the store the same way the subscription
would push them, so the endpoint, the classification, the clustering and the
guidance lookup are all exercised offline.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from blackinterface.api import app as app_module
from blackinterface.api import deps
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.alarm import Alarm, AlarmClass
from blackinterface.domain.scope import ScopeRef
from blackinterface.store.db import Database

BASE = datetime.fromisoformat("2026-08-13T05:04:16.727860+00:00")
SAS_TREE = Path(__file__).parent.parent / "fixtures" / "sas_tree.json"


def _alarm(
    event_id: str,
    device: str,
    point: str,
    klass: AlarmClass,
    severity: int,
    *,
    message: str = "",
    category: str = "",
    offset_ms: int = 0,
    actor: str | None = None,
) -> Alarm:
    return Alarm(
        event_id=event_id,
        subject=ScopeRef.device(device),
        point=ScopeRef.point(point),
        klass=klass,
        message=message,
        severity=severity,
        category=category,
        actor=actor,
        t_active=BASE + timedelta(milliseconds=offset_ms),
    )


@pytest.fixture
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("alarms")
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


@pytest.fixture
def served(client: TestClient) -> StationStore:
    """The store the endpoints are reading, once the app has started it."""
    return deps.get_store()


@pytest.fixture
def loaded(served: StationStore) -> StationStore:
    """A fixture station with a small, deliberately mixed alarm set."""
    device = next(iter(served.graph.devices)).id
    bay = device.split(".")[0]
    served.alarms.load_snapshot(
        [
            _alarm(
                "a-status",
                device,
                f"{device}.PosSt",
                AlarmClass.STATUS,
                200,
                message="CB STATUS",
                category="Discrete Alarm",
            ),
            _alarm(
                "a-fault",
                f"{bay}.MMXU1",
                f"{bay}.MMXU1.Vlin",
                AlarmClass.FAULT,
                650,
                message="ABNORMAL VOLTAGE",
                category="Limit Alarm",
                offset_ms=9,
            ),
        ]
    )
    return served


def test_alarms_hides_switch_positions_by_default(client: TestClient, loaded: StationStore) -> None:
    """The single most important default in this module.

    A healthy station annunciates 90 position alarms; if they arrive by default
    the pane is the wall of noise the product exists to replace.
    """
    body = client.get("/api/alarms?scope=station").json()
    points = [a["point"] for a in body["alarms"]]
    assert any("Vlin" in p for p in points), "the fault must be shown"
    assert not any("PosSt" in p for p in points), "positions are evidence, not alarms"
    # The counts still report them, so nothing is hidden — only demoted.
    assert body["counts"]["status"] == 1
    assert body["counts"]["fault"] == 1


def test_alarms_can_be_asked_for_the_noise(client: TestClient, loaded: StationStore) -> None:
    body = client.get("/api/alarms?scope=station&include_status=true").json()
    assert any("PosSt" in a["point"] for a in body["alarms"])


def test_alarms_carry_evidence(client: TestClient, loaded: StationStore) -> None:
    """ADR-0013: a facet that makes a claim says how far it can be trusted."""
    body = client.get("/api/alarms?scope=station").json()
    evidence = body["evidence"]
    assert evidence["tool"] == "alarms"
    assert evidence["subject"] == "station"
    codes = {limit["code"] for limit in evidence["limits"]}
    # OneATS never populates the A&C Quality field, so no alarm can assert the
    # quality of the point behind it. Saying so beats implying GOOD (I2).
    assert "quality_not_good" in codes


def test_unknown_scope_is_404_not_a_quiet_fallback(
    client: TestClient, loaded: StationStore
) -> None:
    assert client.get("/api/alarms?scope=bay:NOPE").status_code == 404
    assert client.get("/api/incidents?scope=bay:NOPE").status_code == 404


def test_incidents_group_and_attach_guidance(client: TestClient, loaded: StationStore) -> None:
    body = client.get("/api/incidents?scope=station").json()
    assert len(body["incidents"]) == 1
    incident = body["incidents"][0]
    assert incident["severity"] == 650
    playbook = incident["playbook"]
    assert playbook is not None, "ABNORMAL VOLTAGE has a bundled playbook"
    assert playbook["id"] == "abnormal-voltage"
    assert playbook["steps"], "guidance with no steps is not guidance"


def test_open_incidents_are_newest_first(client: TestClient, served: StationStore) -> None:
    """The pane should not bury the latest burst at the bottom."""
    device = next(iter(served.graph.devices)).id
    bay = device.split(".")[0]
    served.alarms.load_snapshot(
        [
            _alarm(
                "old-fault",
                f"{bay}.MMXU1",
                f"{bay}.MMXU1.Vlin",
                AlarmClass.FAULT,
                650,
                message="ABNORMAL VOLTAGE",
                category="Limit Alarm",
                offset_ms=0,
            ),
            _alarm(
                "new-fault",
                device,
                f"{device}.TimeFail",
                AlarmClass.FAULT,
                360,
                message="TIME SYNC FAIL",
                category="Discrete Alarm",
                offset_ms=5000,
            ),
        ]
    )
    body = client.get("/api/incidents?scope=station").json()
    assert len(body["incidents"]) == 2
    assert body["incidents"][0]["id"] == "new-fault"


def test_guidance_is_labelled_draft(client: TestClient, loaded: StationStore) -> None:
    """Unapproved guidance must not look identical to approved guidance.

    Nothing bundled has been through operational review, and the pane renders
    this field — see ADR-0027 §3.
    """
    body = client.get("/api/incidents?scope=station").json()
    assert body["incidents"][0]["playbook"]["status"] == "draft"


def test_operator_action_produces_no_incident(client: TestClient, served: StationStore) -> None:
    """Throwing a switch on purpose is not a fault — the demo-safety case."""
    device = next(iter(served.graph.devices)).id
    served.alarms.load_snapshot(
        [
            _alarm(
                "a-act",
                device,
                f"{device}.PosSt",
                AlarmClass.ACTION,
                200,
                message="CB STATUS",
                category="Discrete Alarm",
                actor="Administrator@OneATS_DataEditor:anhtdq",
            )
        ]
    )
    body = client.get("/api/incidents?scope=station").json()
    assert body["incidents"] == []


def test_stream_opens_with_the_alarm_cadence(client: TestClient, loaded: StationStore) -> None:
    """`/api/live` carries alarms too, so a client needs no extra fetch."""
    body: dict[str, Any] = client.get("/api/live").json()
    assert "alarm" in body
    assert body["alarm"]["has_snapshot"] is True
    assert body["alarm"]["counts"]["fault"] == 1


def test_dismiss_hides_open_incident_and_moves_to_history(
    client: TestClient, loaded: StationStore
) -> None:
    open_before = client.get("/api/incidents?scope=station").json()
    assert len(open_before["incidents"]) == 1
    incident_id = open_before["incidents"][0]["id"]

    dismissed = client.post(f"/api/incidents/{incident_id}/dismiss?scope=station").json()
    assert dismissed["dismissed_at"]
    assert dismissed["id"] == incident_id

    open_after = client.get("/api/incidents?scope=station").json()
    assert open_after["incidents"] == []

    history = client.get("/api/incidents?scope=station&status=dismissed").json()
    assert len(history["incidents"]) == 1
    assert history["incidents"][0]["dismissed_at"]


def test_dismiss_unknown_incident_is_404(client: TestClient, loaded: StationStore) -> None:
    assert client.post("/api/incidents/missing/dismiss?scope=station").status_code == 404


# --------------------------------------------------------------- scope reach
# Regression: filtering alarms with `ScopeRef.contains` made every voltage
# level, busbar and transformer scope report an empty pane on a station full of
# faults. That method returns False for those kinds *because membership needs
# the graph* — its docstring says so — and reading that as "not a member" is the
# bug. Membership now goes through `bays_in`, like `summary.py` always did.


def _voltage_level_of(served: StationStore, bay_id: str) -> str | None:
    from blackinterface.domain.scope import ScopeRef, bays_in

    graph = served.graph
    levels = {b.voltage_level for b in graph.busbars if b.voltage_level}
    for level in levels:
        if bay_id in bays_in(graph, ScopeRef.voltage_level(level)):
            return level
    return None


def test_voltage_level_scope_reaches_the_alarms_in_its_bays(
    client: TestClient, loaded: StationStore
) -> None:
    device = next(iter(loaded.graph.devices)).id
    bay = device.split(".")[0]
    level = _voltage_level_of(loaded, bay)
    if level is None:
        pytest.skip("fixture has no voltage level covering that bay")

    body = client.get(f"/api/alarms?scope=vl:{level}").json()
    assert body["alarms"], (
        f"vl:{level} covers bay {bay}, which has a fault — an empty list here is "
        "the regression this test exists for"
    )
    assert client.get(f"/api/incidents?scope=vl:{level}").json()["incidents"]


def test_bay_scope_still_reaches_its_own_alarms(client: TestClient, loaded: StationStore) -> None:
    device = next(iter(loaded.graph.devices)).id
    bay = device.split(".")[0]
    body = client.get(f"/api/alarms?scope=bay:{bay}").json()
    assert body["alarms"]


def test_an_unrelated_bay_stays_empty(client: TestClient, loaded: StationStore) -> None:
    """The opposite guard: widening the reach must not make everything match."""
    device = next(iter(loaded.graph.devices)).id
    mine = device.split(".")[0]
    other = next((b.id for b in loaded.graph.bays if b.id != mine and b.id not in device), None)
    if other is None:
        pytest.skip("fixture has only one bay")
    body = client.get(f"/api/alarms?scope=bay:{other}").json()
    assert body["alarms"] == []
