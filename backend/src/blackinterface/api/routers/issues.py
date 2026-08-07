"""Validation issues for the loaded station, grouped for the UI (GĐ 1.5 lô 3)."""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.api.authz import requires
from blackinterface.api.deps import get_store
from blackinterface.api.mappers import issue_out
from blackinterface.api.schemas import IssuesOut
from blackinterface.domain.authz import Capability

router = APIRouter()


@router.get(
    "/api/issues",
    response_model=IssuesOut,
    dependencies=[requires(Capability.STATION_READ)],
)
async def list_issues() -> IssuesOut:
    graph = get_store().graph
    return IssuesOut(issues=[issue_out(i) for i in graph.all_issues()])
