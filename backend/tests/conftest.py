"""Shared pytest fixtures.

Unit tests must run without a DataServer. Anything needing the live server
goes in tests/integration/ and carries @pytest.mark.live.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from blackinterface.api import authz
from blackinterface.domain.authz import Role, build_principal
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
    """Dumped OneATS address space (DEMO_SAS v654, 2026-08-06).

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


@pytest.fixture(autouse=True)
def signed_in() -> Iterator[None]:
    """Every test runs as a signed-in account unless it says otherwise.

    Autouse because the alternative is a login call at the top of a hundred
    tests that are about topology, and because the *default* for a test should
    be the ordinary case: somebody is using the application.

    The roles are `operator + engineer` — a legal combination and a real one,
    the lightly-manned station of ADR-0016 section 1 — chosen because between
    them they reach both the operating and the engineering surface.

    Two modules deliberately opt out by calling `authz.use()` themselves:
    `test_authz.py` swaps in a narrower principal per test, and
    `test_accounts.py` clears the override entirely so it exercises the real
    cookie path. Their fixtures run after this one, so they win.
    """
    authz.use(build_principal("test", [Role.OPERATOR, Role.ENGINEER]))
    yield
    authz.use(None)
