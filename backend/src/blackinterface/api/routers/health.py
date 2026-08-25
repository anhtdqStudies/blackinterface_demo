"""Is there a model, where did it come from, and can it be re-read."""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.api.authz import public, requires
from blackinterface.api.deps import get_store
from blackinterface.api.schemas import HealthOut
from blackinterface.domain.authz import Capability

router = APIRouter()


# Public: whether the process is up has to be answerable before anyone signs in,
# and by whatever watches it. It names the model source, which is why nothing
# else about the station is on it.
@router.get("/api/health", response_model=HealthOut, dependencies=[public()])
async def health() -> HealthOut:
    store = get_store()
    return HealthOut(
        ok=store.loaded,
        loaded=store.loaded,
        source=store.source_label,
        load_error=store.load_error,
        load_seconds=store.load_seconds,
        project_id=store.project.id if store.project else None,
        project_name=store.project.name if store.project else None,
    )


@router.post(
    "/api/reload",
    response_model=HealthOut,
    dependencies=[requires(Capability.MODEL_CONNECT)],
)
async def reload_station() -> HealthOut:
    """Re-read the current source: the active project's DataServer (updating
    its snapshot), else BI_SOURCE. Writes nothing to OneATS (I1)."""
    await get_store().try_reload()
    return await health()
