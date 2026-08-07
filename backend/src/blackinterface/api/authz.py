"""The facet-layer permission gate (ADR-0016 section 4).

One place decides whether a call is allowed, and this is it. The reason it is
here and not in the frontend: the agent calls the same facets a person does
(ADR-0010), so a check living in a Vue component is not a permission at all —
it only hides a button. Anything that says something about the station passes
through `requires()` on its way in.

**Deny by default.** A facet that declares nothing must not run; that is checked
two ways, because each fails differently. `tools/check.py` reads the decorators
statically, and `test_authz.py` walks the assembled app — a router registered
but never scanned would slip past the first, a file that does not import past
the second.

Three declarations, and the difference between the first two is the difference
between two error codes a caller has to be able to tell apart:

    requires(Capability.X)  needs a signed-in caller holding X       403
    requires()              needs a signed-in caller, nothing more   401 if not
    public()                needs nobody at all — sign-in, liveness

Who the caller *is* comes from `accounts.py`. This module only decides what
that caller may do.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Depends, Request, params
from fastapi.routing import APIRoute

from blackinterface.api import accounts
from blackinterface.domain.authz import Capability, Principal
from blackinterface.errors import ForbiddenError, UnauthenticatedError
from blackinterface.logs import get_logger

log = get_logger(__name__)

#: Stamped on every guard so the assembled app can be asked what each route
#: demands. Without it, "did this facet declare anything" is unanswerable at
#: runtime and the deny-by-default rule rests on review alone.
REQUIRES_ATTR = "__bi_requires__"

#: Stamped on `public()` guards only. Kept separate from an empty capability set
#: because "anyone at all" and "any signed-in caller" are different decisions
#: and the tests assert on each list by name.
PUBLIC_ATTR = "__bi_public__"

#: Test-only override. Set through `use()`, never from configuration — the
#: point of a module global here is that only Python running in this process can
#: reach it, exactly like `deps.store`.
_override: Principal | None = None


def get_principal(request: Request) -> Principal:
    """The caller of this request."""
    if _override is not None:
        return _override
    return accounts.resolve(request)


#: The FastAPI way to say "give this handler the caller". Built once at module
#: level rather than inline in each signature: a call in a default argument is
#: evaluated at definition time, which is the trap ruff's B008 exists to catch.
CALLER: Principal = Depends(get_principal)


def use(principal: Principal | None) -> None:
    """Run as somebody else. For tests, and for nothing else.

    `None` puts the real resolution back, which is what a test asserting on the
    login flow itself needs.
    """
    global _override
    _override = principal


def requires(*capabilities: Capability) -> params.Depends:
    """Declare what a facet demands. Every route must carry one of these.

    Passing no capability means *any signed-in caller* and is allowed only for
    facets that assert nothing about the station — today that is `/api/me` and
    the sign-out call. It is still an explicit declaration, so "this facet is
    open" is something somebody wrote down rather than a line somebody forgot;
    `test_authz.py` holds the exact list of paths permitted to use it.
    """
    demanded = frozenset(capabilities)

    async def guard(principal: Principal = CALLER) -> Principal:
        if principal.is_anonymous:
            # 401, not 403: the caller has a way out of this one, and the UI
            # needs to tell "sign in" apart from "you are not allowed".
            raise UnauthenticatedError("bạn cần đăng nhập")
        missing = sorted(c.value for c in demanded if not principal.can(c))
        if missing:
            log.warning(
                "denied",
                user=principal.user,
                roles=[r.value for r in principal.roles],
                missing=missing,
            )
            raise ForbiddenError(
                "this account does not have the required permission",
                missing=missing,
                roles=[r.value for r in principal.roles],
            )
        return principal

    setattr(guard, REQUIRES_ATTR, demanded)
    return params.Depends(dependency=guard)


def public() -> params.Depends:
    """No identity needed. Only for facets that must work *before* signing in.

    A separate function rather than a flag on `requires()` so that "reachable by
    anyone who can open the port" is a word you have to type, and one that shows
    up in a grep.
    """

    async def open_gate() -> None:
        return None

    setattr(open_gate, REQUIRES_ATTR, frozenset())
    setattr(open_gate, PUBLIC_ATTR, True)
    return params.Depends(dependency=open_gate)


def iter_api_routes(app: Any) -> Iterator[APIRoute]:
    """Every real endpoint in an assembled app, however deeply it is nested.

    `app.routes` is not a flat list, and its shape is a moving target: on
    FastAPI 0.141 each `include_router` leaves one `_IncludedRouter` wrapper
    holding the real endpoints behind `original_router`, so reading the top
    level finds no endpoints at all. Descending on *any* attribute that leads to
    routes keeps this working across that churn — which matters, because the
    failure mode is a caller believing it checked every facet after checking
    none.

    One deliberate limitation: a capability declared through
    `include_router(dependencies=[...])` rather than on the route decorator is
    not visible here. That combination fails closed — the route reads as
    undeclared and the gate test fails — which is the right way round.
    """
    seen: set[int] = set()

    def walk(node: Any) -> Iterator[APIRoute]:
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        for route in getattr(node, "routes", ()):
            if isinstance(route, APIRoute):
                yield route
            else:
                yield from walk(route)
        for attr in ("original_router", "app"):
            yield from walk(getattr(node, attr, None))

    yield from walk(app)


def declared_capabilities(route: APIRoute) -> frozenset[Capability] | None:
    """What this route demands, or `None` if it never declared — which is a bug.

    `None` and `frozenset()` are different answers and must stay that way: the
    first is a facet nobody gated, the second is one deliberately left open.
    """
    for dependency in route.dependant.dependencies:
        demanded = getattr(dependency.call, REQUIRES_ATTR, None)
        if demanded is not None:
            assert isinstance(demanded, frozenset)
            return demanded
    return None


def is_public(route: APIRoute) -> bool:
    """Declared reachable without signing in."""
    return any(
        getattr(dependency.call, PUBLIC_ATTR, False) for dependency in route.dependant.dependencies
    )
