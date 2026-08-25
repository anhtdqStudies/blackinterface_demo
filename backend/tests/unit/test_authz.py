"""Permission rules that must not quietly change (ADR-0016).

Three kinds of test live here, and the middle one is the reason the file exists:

  * the role table says what the ADR says it says
  * **no facet escapes the gate** — walked over the assembled app, so a router
    that was added and registered but never given a `requires=` fails here even
    though nothing about it looks wrong
  * the separation-of-duty rules hold under role *combinations*, which is where
    a union-based model would otherwise leak
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from blackinterface.api import app as app_module
from blackinterface.api import authz, deps
from blackinterface.api.authz import (
    declared_capabilities,
    is_public,
    iter_api_routes,
    requires,
)
from blackinterface.api.source import StationStore
from blackinterface.config import Settings
from blackinterface.domain.authz import (
    ANONYMOUS,
    ROLES,
    Capability,
    Principal,
    Role,
    RoleConflictError,
    build_principal,
    capabilities_for,
    parse_roles,
)
from blackinterface.store.db import Database
from tests.conftest import SAS_TREE

#: Facets reachable with no identity at all. Signing in has to work before you
#: have one; liveness has to answer whatever is watching the process; `/api/me`
#: is how the frontend finds out whether to show a login screen, and it
#: discloses nothing to an anonymous caller. Asserted by equality, not by
#: subset — a fourth entry appearing here is a decision, not a detail.
PUBLIC_PATHS = {"/api/login", "/api/health", "/api/me"}

#: Facets that need a signed-in caller but no particular capability.
OPEN_TO_ANY_CALLER = {"/api/logout", "/api/password"}


def _api_routes() -> list[APIRoute]:
    routes = [r for r in iter_api_routes(app_module.app) if r.path.startswith("/api/")]
    # Guard against the whole file passing vacuously: an empty list would make
    # every assertion below trivially true. This is not hypothetical — the first
    # version of this helper read `app.routes` directly and found nothing,
    # because an included router is one nested wrapper, not its endpoints.
    assert len(routes) > 5, f"only found {len(routes)} routes; the walk is broken, not the app"
    return routes


# --------------------------------------------------------------- the gate runs


def test_every_facet_declares_a_capability() -> None:
    """Deny by default, checked against the app that actually got assembled.

    `tools/check.py` reads the same rule off the decorators. This one catches
    what a source scan cannot: a router included from somewhere the scan does
    not look, or a route built at runtime.
    """
    undeclared = sorted(
        f"{sorted(r.methods)[0]} {r.path}"
        for r in _api_routes()
        if declared_capabilities(r) is None
    )
    assert not undeclared, (
        f"facets with no requires=: {undeclared}. A facet that declares nothing serves "
        f"everybody (ADR-0016 section 4)."
    )


def test_a_facet_that_forgets_the_gate_is_caught() -> None:
    """The detector detects. Without this, the test above could be vacuously
    green — it would pass just as happily if `declared_capabilities` always
    returned a value."""
    forgetful = APIRouter()

    @forgetful.get("/api/forgot")
    async def forgot() -> dict[str, str]:
        return {}

    app = FastAPI()
    app.include_router(forgetful)
    route = next(r for r in iter_api_routes(app) if r.path == "/api/forgot")
    assert declared_capabilities(route) is None


def test_the_public_surface_is_exactly_three_paths() -> None:
    """The list of facets reachable without signing in is the thing to review."""
    assert {r.path for r in _api_routes() if is_public(r)} == PUBLIC_PATHS


def test_only_identity_facets_are_open_to_any_signed_in_caller() -> None:
    open_paths = {
        r.path
        for r in _api_routes()
        if declared_capabilities(r) == frozenset() and not is_public(r)
    }
    assert open_paths == OPEN_TO_ANY_CALLER


def test_reading_the_station_needs_station_read() -> None:
    for route in _api_routes():
        if route.path.startswith(
            ("/api/station", "/api/bays", "/api/busbars", "/api/live", "/api/issues")
        ):
            assert declared_capabilities(route) == frozenset({Capability.STATION_READ}), route.path


# ------------------------------------------------------------ enforcement live


@pytest.fixture
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    if not SAS_TREE.exists():
        pytest.skip(f"fixture missing: {SAS_TREE}")
    data_dir = tmp_path_factory.mktemp("authz")
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
    authz.use(None)


def _as(principal: Principal) -> None:
    authz.use(principal)


def test_an_operator_reads_the_station_but_not_the_connections(client: TestClient) -> None:
    """The permission that separates the two surfaces, exercised end to end."""
    _as(build_principal("op", [Role.OPERATOR]))
    assert client.get("/api/station").status_code == 200
    denied = client.get("/api/projects")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"
    assert denied.json()["error"]["detail"]["missing"] == ["model.connect"]


def test_an_engineer_reads_the_connections(client: TestClient) -> None:
    _as(build_principal("eng", [Role.ENGINEER]))
    assert client.get("/api/projects").status_code == 200


def test_admin_holds_no_operational_permission(client: TestClient) -> None:
    """Grants rights to others; sees no plant. ADR-0016 section 3, rule 2."""
    _as(build_principal("adm", [Role.ADMIN]))
    assert client.get("/api/station").status_code == 403
    assert client.get("/api/me").status_code == 200  # still knows who it is


def test_nobody_signed_in_is_401_not_403(client: TestClient) -> None:
    """The two must not be confused: one is fixed by signing in, the other is
    not, and a UI that cannot tell them apart offers the wrong remedy."""
    _as(ANONYMOUS)
    refused = client.get("/api/station")
    assert refused.status_code == 401
    assert refused.json()["error"]["code"] == "unauthenticated"


def test_me_answers_anonymously_without_disclosing_anything(client: TestClient) -> None:
    """How the frontend learns it must show a login screen."""
    _as(ANONYMOUS)
    body = client.get("/api/me").json()
    assert body["authenticated"] is False
    assert body["user"] == "" and body["roles"] == [] and body["capabilities"] == []


def test_me_reports_capabilities_not_just_roles(client: TestClient) -> None:
    _as(build_principal("sup", [Role.SUPERVISOR]))
    body = client.get("/api/me").json()
    assert body["user"] == "sup"
    assert body["roles"] == ["supervisor"]
    assert "control.sign" in body["capabilities"]


def test_evidence_names_who_asked(client: TestClient) -> None:
    """No actor on the record, no audit trail later (ADR-0016 section 5)."""
    _as(build_principal("nguyen", [Role.OPERATOR]))
    body = client.get("/api/summary", params={"scope": "bay:D03"}).json()
    assert body["evidence"]["actor"] == "nguyen"


# ------------------------------------------------------- separation of duty


def test_engineer_never_signs() -> None:
    assert Capability.CONTROL_SIGN not in ROLES[Role.ENGINEER]


@pytest.mark.parametrize("other", [Role.SUPERVISOR])
def test_engineer_cannot_be_combined_with_a_signing_role(other: Role) -> None:
    """The rule the union alone would break: engineer + supervisor would
    otherwise add up to an account that both edits the model and signs the
    operations relying on it."""
    with pytest.raises(RoleConflictError):
        capabilities_for([Role.ENGINEER, other])
    with pytest.raises(RoleConflictError):
        parse_roles(f"engineer,{other.value}")


def test_engineer_may_be_combined_with_a_drafting_role() -> None:
    """Only signing is forbidden. A one-person site still has to work."""
    caps = capabilities_for([Role.ENGINEER, Role.OPERATOR])
    assert Capability.CONTROL_DRAFT in caps
    assert Capability.MODEL_PUBLISH in caps
    assert Capability.CONTROL_SIGN not in caps


def test_maintenance_holds_no_control() -> None:
    """Per ATS's own matrix (A B D F). Rule 3."""
    assert not {Capability.CONTROL_DRAFT, Capability.CONTROL_SIGN} & ROLES[Role.MAINTENANCE]


def test_several_roles_add_up() -> None:
    caps = capabilities_for([Role.OPERATOR, Role.MAINTENANCE])
    assert ROLES[Role.OPERATOR] <= caps and ROLES[Role.MAINTENANCE] <= caps


def test_no_roles_grants_nothing() -> None:
    assert capabilities_for([]) == frozenset()


def test_unknown_role_is_rejected_by_name() -> None:
    with pytest.raises(ValueError, match="unknown role"):
        parse_roles("operatr")


def test_roles_are_parsed_in_order_without_duplicates() -> None:
    assert parse_roles(" operator , maintenance ,operator ") == (Role.OPERATOR, Role.MAINTENANCE)


def test_every_role_grants_something() -> None:
    """A role bundle that grants nothing is a typo, not a design."""
    assert all(ROLES[role] for role in Role)


# ----------------------------------------------------------------- the agent


def test_the_agent_mints_no_identity_of_its_own() -> None:
    """ADR-0016 section 5: the agent runs under the permissions of whoever asked.

    Structural while `agent/` is still empty (GD 2). It is here now because the
    moment the agent grows a way to build its own `Principal` is the moment it
    can read more than its caller, and that is the mistake worth failing on
    rather than reviewing for.
    """
    import blackinterface.agent as agent_pkg

    minting = {"Principal", "build_principal", "capabilities_for", "ROLES"}
    assert not minting & set(vars(agent_pkg)), (
        "agent/ must borrow the caller's principal, never construct one"
    )


def test_requires_reports_what_it_demands() -> None:
    gate = requires(Capability.STATION_READ, Capability.AGENT_ASK)
    assert getattr(gate.dependency, authz.REQUIRES_ATTR) == frozenset(
        {Capability.STATION_READ, Capability.AGENT_ASK}
    )
