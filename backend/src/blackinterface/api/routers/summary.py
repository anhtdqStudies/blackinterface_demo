"""One scope, one answer, one evidence record.

Kept in its own router rather than folded into `station.py` because it is a
different kind of endpoint: everything there returns a slice of the model, and
this returns a *judgement* about a slice — which is why it is the only one that
has to say how far it can be trusted.

The scope grammar is enforced at the door: an unparseable or unknown scope is a
400 or a 404, never a quiet fallback to the whole station (ADR-0010).
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from blackinterface.api.authz import CALLER, requires
from blackinterface.api.deps import get_store
from blackinterface.api.schemas import SummaryOut
from blackinterface.api.summary import build_summary
from blackinterface.domain.authz import Capability, Principal

router = APIRouter()


# `station.read`, not `agent.ask`: this summary is computed, not generated
# (ADR-0005). Whoever may look at the station may read what it adds up to.
@router.get(
    "/api/summary",
    response_model=SummaryOut,
    dependencies=[requires(Capability.STATION_READ)],
)
async def summary(
    scope: str = Query("station", description="Scope ref, e.g. station, vl:220kV, bay:D03"),
    principal: Principal = CALLER,
) -> SummaryOut:
    """How this part of the station is doing, with the evidence behind it."""
    return build_summary(get_store(), scope, actor=principal.user)
