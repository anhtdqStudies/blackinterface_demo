"""Alarms, and the incidents they add up to.

Two endpoints rather than one because they answer different questions. `/api/
alarms` is the list — what is currently annunciated in this scope. `/api/
incidents` is the judgement — how those alarms group, and what the guidance says
about each group.

Scope grammar is enforced at the door like everywhere else: an unknown scope is
a 404, never a quiet fallback to the whole station (ADR-0010).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from blackinterface.api.alarms import build_alarms, build_incidents, dismiss_incident
from blackinterface.api.authz import CALLER, requires
from blackinterface.api.deps import get_alarms, get_incident_dismissals, get_store
from blackinterface.api.schemas import AlarmsOut, IncidentOut, IncidentsOut
from blackinterface.domain.authz import Capability, Principal

router = APIRouter()


@router.get(
    "/api/alarms",
    response_model=AlarmsOut,
    dependencies=[requires(Capability.ALARM_READ)],
)
async def alarms(
    scope: str = Query("station", description="Scope ref, e.g. station, bay:D03"),
    include_status: bool = Query(
        False,
        description=(
            "Include switch-position and configuration alarms. Off by default: a "
            "healthy station annunciates 90 of them and they are evidence, not faults."
        ),
    ),
    principal: Principal = CALLER,
) -> AlarmsOut:
    """Active alarms for one scope, classified, with evidence."""
    return build_alarms(
        get_store(),
        get_alarms(),
        scope,
        actor=principal.user,
        include_status=include_status,
    )


@router.get(
    "/api/incidents",
    response_model=IncidentsOut,
    dependencies=[requires(Capability.ALARM_READ)],
)
async def incidents(
    scope: str = Query("station", description="Scope ref, e.g. station, bay:D03"),
    window_ms: int | None = Query(
        None,
        ge=10,
        le=60_000,
        description=("Clustering window. Default 200 ms, measured: a real cascade spanned 87 ms."),
    ),
    status: Literal["open", "dismissed"] = Query(
        "open",
        description=(
            "Open incidents need attention. Dismissed returns local history "
            "after an operator pressed Done — not OneATS acknowledgement."
        ),
    ),
    principal: Principal = CALLER,
) -> IncidentsOut:
    """Alarms grouped into incidents, each with its handling guidance."""
    return build_incidents(
        get_store(),
        get_alarms(),
        scope,
        actor=principal.user,
        window_ms=window_ms,
        status=status,
        dismissals=get_incident_dismissals(),
    )


@router.post(
    "/api/incidents/{incident_id}/dismiss",
    response_model=IncidentOut,
    dependencies=[requires(Capability.ALARM_READ)],
)
async def dismiss(
    incident_id: str,
    scope: str = Query(..., description="Scope ref the operator was viewing"),
    window_ms: int | None = Query(
        None,
        ge=10,
        le=60_000,
        description="Clustering window — must match the open-incidents view.",
    ),
    principal: Principal = CALLER,
) -> IncidentOut:
    """Mark one open incident as handled locally. Does not ack on OneATS (I1)."""
    return dismiss_incident(
        get_store(),
        get_alarms(),
        scope,
        incident_id,
        actor=principal.user,
        window_ms=window_ms,
        dismissals=get_incident_dismissals(),
    )
