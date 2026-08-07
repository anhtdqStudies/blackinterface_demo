"""Who am I, and what may I do (ADR-0016).

The frontend hides what the caller cannot use, and this is where it learns what
that is. It reports *capabilities*, not just role names, so a component asks
"may this account sign" rather than "is this account a supervisor" — otherwise
adding a role means editing every component that named the old ones.

Hiding is a courtesy, never the enforcement. The enforcement is `requires()` on
each facet, and it runs whether or not anything was hidden.

Public, unlike every other read: the frontend has to be able to ask "is anybody
signed in" *before* it can know to show a login screen. It discloses nothing —
to an anonymous caller it answers with an empty identity.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from blackinterface.api.authz import get_principal, public
from blackinterface.api.routers.auth import me_out
from blackinterface.api.schemas import MeOut

router = APIRouter()


@router.get("/api/me", response_model=MeOut, dependencies=[public()])
async def me(request: Request) -> MeOut:
    """The current caller, or an empty identity when nobody is signed in.

    Resolved through `get_principal`, not by reading the cookie here: every
    facet must agree about who is calling, and a second way of working that out
    is a second answer waiting to disagree with the first.
    """
    return me_out(get_principal(request))
