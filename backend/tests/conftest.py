"""Shared pytest fixtures.

Unit tests must run without a DataServer. Anything needing the live server
goes in tests/integration/ and carries @pytest.mark.live.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from blackinterface.domain.models import StationGraph
from blackinterface.domain.observation import StationObs
from blackinterface.domain.topology import build_station
from blackinterface.integration.dump import load_dump

FIXTURES = Path(__file__).parent / "fixtures"
SAS_TREE = FIXTURES / "sas_tree.json"

REGENERATE = (
    "python tools/probe_dataserver.py --dump --slim --depth 4 "
    "--out backend/tests/fixtures/sas_tree.json"
)


@pytest.fixture(scope="session")
def sas_tree() -> dict[str, Any]:
    """Dumped OneATS address space (DEMO_SAS v654, 2026-08-04).

    Shape: {"meta": {ModelName, ModelVersion, captured_at, endpoint},
            "nodes": [...]}
    """
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE} - regenerate with: {REGENERATE}")
    result: dict[str, Any] = json.loads(SAS_TREE.read_text(encoding="utf-8"))
    return result


@pytest.fixture(scope="session")
def observation() -> StationObs:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE} - regenerate with: {REGENERATE}")
    return load_dump(SAS_TREE)


@pytest.fixture(scope="session")
def station(observation: StationObs) -> StationGraph:
    """The full pipeline, offline: dump -> observation -> templates -> graph."""
    return build_station(observation)
