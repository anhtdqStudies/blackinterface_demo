"""Signing in, signing out, changing a password (ADR-0017).

Three endpoints and no logic: the work is in `api/accounts.py`, so that what
this file shows is the surface. `/api/login` is the one facet in the whole API
declared `public()` besides liveness — it has to work before anybody has an
identity, which is precisely why it is the one to read carefully.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from blackinterface.api import accounts
from blackinterface.api.authz import CALLER, get_principal, public, requires
from blackinterface.api.schemas import LoginIn, MeOut, PasswordChangeIn
from blackinterface.config import get_settings
from blackinterface.domain.authz import Principal

router = APIRouter()


def me_out(principal: Principal) -> MeOut:
    return MeOut(
        user=principal.user,
        display_name=principal.display_name,
        roles=[r.value for r in principal.roles],
        capabilities=sorted(c.value for c in principal.capabilities),
        authenticated=not principal.is_anonymous,
        auth_mode=get_settings().auth,
    )


@router.post("/api/login", response_model=MeOut, dependencies=[public()])
async def login(body: LoginIn, response: Response) -> MeOut:
    """Verify a password and start a session.

    Writes a row to the local SQLite store and sets a cookie. Nothing here
    reaches OneATS (I1) — this endpoint is about who is looking at the station,
    not about the station.
    """
    return me_out(accounts.sign_in(body.username, body.password, response))


@router.post("/api/logout", response_model=MeOut, dependencies=[requires()])
async def logout(request: Request, response: Response) -> MeOut:
    """End the session server-side and clear the cookie."""
    accounts.sign_out(request, response)
    # Re-resolved after the session is gone, so the body says what the next
    # request will find rather than what this one arrived with.
    return me_out(get_principal(request))


@router.post("/api/password", response_model=MeOut, dependencies=[requires()])
async def change_password(body: PasswordChangeIn, principal: Principal = CALLER) -> MeOut:
    """Change your own password. The current one has to be given again.

    Only your own: changing somebody else's belongs with `account.manage` and
    an audit record, and that screen does not exist yet. Better absent than
    half-built.
    """
    accounts.change_password(principal, body.current_password, body.new_password)
    return me_out(principal)
