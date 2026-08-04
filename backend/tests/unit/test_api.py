"""Domain API contract. Runs against the fixture — no DataServer, no LLM (I4)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from blackinterface.api import app as app_module
from blackinterface.api.source import Settings, StationStore
from tests.conftest import SAS_TREE


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    app_module.store = StationStore(Settings(source="fixture", fixture=SAS_TREE))
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


def test_no_write_endpoint_exists(client: TestClient) -> None:
    """AGENTS.md I1 enforced structurally: /api/reload is the only POST."""
    paths = client.get("/openapi.json").json()["paths"]
    writes = {
        f"{method.upper()} {path}"
        for path, ops in paths.items()
        for method in ops
        if method.lower() in {"post", "put", "patch", "delete"}
    }
    assert writes == {"POST /api/reload"}
