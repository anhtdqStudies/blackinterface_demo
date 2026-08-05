"""Domain API contract. Runs against the fixture — no DataServer, no LLM (I4)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from blackinterface.api import app as app_module
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.observation import StationObs
from blackinterface.errors import SourceUnavailableError
from blackinterface.integration.dump import load_dump
from tests.conftest import SAS_TREE


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("data")
    app_module.database = app_module.Database(data_dir / "test.sqlite")
    app_module.store = StationStore(
        # realtime off: the project tests below use made-up DataServer URLs, and
        # a subscription would be the one thing in this module actually dialling
        # the network. Realtime wiring has its own tests in test_realtime.py.
        Settings(source="fixture", fixture=SAS_TREE, data_dir=data_dir, realtime=False),
        app_module.database,
    )
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_health_reports_a_loaded_model(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["load_error"] is None


def test_station_summary(client: TestClient) -> None:
    body = client.get("/api/station").json()
    assert body["bay_count"] == 13
    assert body["device_count"] == 80
    assert body["coverage"]["position_good"] == 80
    assert set(body["voltage_levels"]) == {"220kV", "110kV", "22kV"}


def test_bays_listing_is_complete(client: TestClient) -> None:
    bays = client.get("/api/bays").json()
    assert {b["id"] for b in bays} >= {"D01", "D03", "D17", "E05", "J01", "DBB"}
    assert all(b["bay_type"] != "UNKNOWN" for b in bays)


def test_bay_detail_exposes_provenance(client: TestClient) -> None:
    """Every state must be traceable back to the DataServer (I3, I6)."""
    body = client.get("/api/bays/D03").json()
    breaker = next(d for d in body["devices"] if d["ln"] == "XCBR1")
    assert breaker["name"] == "271"
    assert breaker["state"] == "CLOSED"
    assert breaker["quality"] == "GOOD"
    assert breaker["source_timestamp"]
    assert breaker["source_ref"].startswith("ns=2;s=")


def test_unknown_bay_is_404(client: TestClient) -> None:
    assert client.get("/api/bays/NOPE").status_code == 404


def test_diagram_endpoint(client: TestClient) -> None:
    body = client.get("/api/diagram/220kV").json()
    assert body["width"] > 0 and body["height"] > 0
    assert len(body["rails"]) == 3
    assert body["symbols"]


def test_unknown_voltage_level_is_404(client: TestClient) -> None:
    assert client.get("/api/diagram/999kV").status_code == 404


def test_energization_endpoint_can_be_joined_onto_the_diagram(
    client: TestClient,
) -> None:
    """The contract the drawing depends on: every rail and conductor names a
    node, and every named node has a verdict. A missing join shows up as an
    uncoloured conductor, which is precisely the thing an operator must not see.
    """
    energized = client.get("/api/energization").json()
    diagram = client.get("/api/diagram").json()
    states = energized["node_state"]

    assert energized["summary"]["mismatched"] == 0
    assert energized["summary"]["compared"] >= 7

    for rail in diagram["rails"]:
        assert rail["node_id"] in states, rail["busbar_id"]
    for edge in diagram["edges"]:
        assert edge["node_id"] in states, edge["id"]
    for junction in diagram["junctions"]:
        assert junction["node_id"] in states, junction["id"]


def test_energization_reports_the_unreadable_busbar_as_unknown(
    client: TestClient,
) -> None:
    """BB29 has no usable IsLive, so it must not be coloured dead (I2)."""
    body = client.get("/api/energization").json()
    assert body["node_state"]["NODE.BB29"] == "UNKNOWN"


def test_no_write_endpoint_exists(client: TestClient) -> None:
    """AGENTS.md I1 enforced structurally: every non-GET endpoint is on this
    allowlist, and each one writes only to the local SQLite store — nothing
    here has a path to OneATS's write surface (that is tools/check.py's job)."""
    paths = client.get("/openapi.json").json()["paths"]
    writes = {
        f"{method.upper()} {path}"
        for path, ops in paths.items()
        for method in ops
        if method.lower() in {"post", "put", "patch", "delete"}
    }
    assert writes == {
        "POST /api/reload",
        "POST /api/projects",
        "POST /api/projects/{project_id}/open",
        "POST /api/projects/{project_id}/refresh",
        "DELETE /api/projects/{project_id}",
    }


def test_errors_share_one_shape(client: TestClient) -> None:
    """One error body for everything, so the generated TS types cover it."""
    body = client.get("/api/bays/NOPE").json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "not_found"
    assert body["error"]["detail"] == {"bay_id": "NOPE"}


# ------------------------------------------------------------------- projects
# The "DataServer" in these tests is the committed fixture: `_observe_opcua`
# is patched on the store instance, so the whole create -> snapshot -> open ->
# refresh -> delete flow runs offline, exactly like every other unit test.


def _serve_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    async def observe(url: str) -> StationObs:
        return load_dump(SAS_TREE).model_copy(update={"source": url})

    monkeypatch.setattr(app_module.store, "_observe_opcua", observe)


def _serve_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def observe(url: str) -> StationObs:
        raise SourceUnavailableError(f"cannot read the OneATS DataServer at {url}", url=url)

    monkeypatch.setattr(app_module.store, "_observe_opcua", observe)


def test_create_project_connects_and_snapshots(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_fixture(monkeypatch)
    body = client.post(
        "/api/projects", json={"name": "Trạm A", "opcua_url": "opc.tcp://10.0.0.5:48050"}
    ).json()
    assert body["ok"] is True and body["error"] is None
    assert body["project"]["active"] is True
    assert body["project"]["has_snapshot"] is True
    assert body["project"]["model_version"]

    health = client.get("/api/health").json()
    assert health["project_name"] == "Trạm A"
    assert health["source"] == "project:Trạm A"
    assert client.get("/api/station").json()["device_count"] == 80


def test_open_project_renders_from_snapshot_without_the_dataserver(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point of the snapshot: reopening must not need the source."""
    _serve_nothing(monkeypatch)
    project = next(p for p in client.get("/api/projects").json() if p["name"] == "Trạm A")
    body = client.post(f"/api/projects/{project['id']}/open").json()
    assert body["ok"] is True
    assert client.get("/api/station").json()["source"].startswith("snapshot:")


def test_refresh_reads_live_and_replaces_the_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_fixture(monkeypatch)
    project = next(p for p in client.get("/api/projects").json() if p["name"] == "Trạm A")
    body = client.post(f"/api/projects/{project['id']}/refresh").json()
    assert body["ok"] is True
    assert body["project"]["snapshot_saved_at"] >= project["snapshot_saved_at"]
    assert not client.get("/api/station").json()["source"].startswith("snapshot:")


def test_create_project_keeps_the_row_when_the_source_is_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wrong URL or a dead server is fixable — do not throw the project away."""
    _serve_nothing(monkeypatch)
    body = client.post(
        "/api/projects", json={"name": "Trạm B", "opcua_url": "opc.tcp://10.9.9.9:48050"}
    ).json()
    assert body["ok"] is False
    assert "cannot read" in body["error"]
    assert body["project"]["has_snapshot"] is False

    _serve_fixture(monkeypatch)
    retry = client.post(f"/api/projects/{body['project']['id']}/refresh").json()
    assert retry["ok"] is True
    assert retry["project"]["has_snapshot"] is True


def test_project_input_is_validated(client: TestClient) -> None:
    no_name = client.post("/api/projects", json={"name": "  ", "opcua_url": "opc.tcp://x:1"})
    assert no_name.status_code == 400
    assert no_name.json()["error"]["code"] == "invalid_input"

    bad_scheme = client.post("/api/projects", json={"name": "X", "opcua_url": "http://not-opc:80"})
    assert bad_scheme.status_code == 400


def test_duplicate_project_name_is_a_conflict(client: TestClient) -> None:
    response = client.post(
        "/api/projects", json={"name": "Trạm A", "opcua_url": "opc.tcp://elsewhere:48050"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_open_unknown_project_is_404(client: TestClient) -> None:
    assert client.post("/api/projects/99999/open").status_code == 404


def test_deleting_the_active_project_unloads_the_model(client: TestClient) -> None:
    listed = {p["name"]: p for p in client.get("/api/projects").json()}
    active = next(p for p in listed.values() if p["active"])
    remaining = client.delete(f"/api/projects/{active['id']}").json()
    assert active["name"] not in {p["name"] for p in remaining}
    assert client.get("/api/health").json()["loaded"] is False
    assert client.get("/api/station").status_code == 503
    # Clean the other test project too, so this module leaves no state behind.
    for project in remaining:
        client.delete(f"/api/projects/{project['id']}")


def test_not_loaded_reports_503_with_a_reason() -> None:
    """A broken source must not look like an empty station."""
    original = app_module.store
    try:
        app_module.store = StationStore(
            Settings(source="fixture", fixture=SAS_TREE.parent / "does-not-exist.json")
        )
        with TestClient(app_module.app, raise_server_exceptions=False) as broken:
            response = broken.get("/api/station")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "model_not_loaded"
        assert "does-not-exist.json" in broken.get("/api/health").json()["load_error"]
    finally:
        app_module.store = original
