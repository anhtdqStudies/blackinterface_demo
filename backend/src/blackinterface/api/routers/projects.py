"""Projects — a name, a DataServer address, and a snapshot of what was there.

Every POST and DELETE here writes to the local SQLite store only. Toward OneATS
this module is as read-only as the rest (I1) — enforced by `tools/check.py`
scanning for write calls, not by trusting this sentence.
"""

from __future__ import annotations

from fastapi import APIRouter

from blackinterface.api.authz import requires
from blackinterface.api.deps import get_store
from blackinterface.api.mappers import project_out
from blackinterface.api.schemas import ProjectCreateIn, ProjectLoadOut, ProjectOut
from blackinterface.domain.authz import Capability
from blackinterface.errors import ConflictError, InvalidInputError, NotFoundError
from blackinterface.logs import get_logger
from blackinterface.store.projects import ProjectRow

log = get_logger(__name__)

router = APIRouter()


def _out(row: ProjectRow) -> ProjectOut:
    store = get_store()
    return project_out(row, active=store.project is not None and store.project.id == row.id)


# Which DataServer this installation is pointed at is an engineering concern,
# not an operating one: `model.connect` is held by `engineer` alone. An operator
# who could repoint the source could change what every other answer describes
# without anything on their screen saying so.
@router.get(
    "/api/projects",
    response_model=list[ProjectOut],
    dependencies=[requires(Capability.MODEL_CONNECT)],
)
async def projects() -> list[ProjectOut]:
    return [_out(p) for p in get_store().projects.list()]


@router.post(
    "/api/projects",
    response_model=ProjectLoadOut,
    dependencies=[requires(Capability.MODEL_CONNECT)],
)
async def create_project(body: ProjectCreateIn) -> ProjectLoadOut:
    """Create a project and immediately try to browse its DataServer.

    Success stores a snapshot and makes the project active. Failure keeps the
    project so the URL can be corrected and retried with /refresh.
    """
    store = get_store()
    name = body.name.strip()
    url = body.opcua_url.strip()
    if not name:
        raise InvalidInputError("project name must not be empty")
    if not url.startswith("opc.tcp://"):
        raise InvalidInputError("the DataServer address must start with opc.tcp://", opcua_url=url)
    if store.projects.get_by_name(name) is not None:
        raise ConflictError(f"a project named {name!r} already exists", name=name)
    row = store.projects.create(name, url)
    return await _load_project(row.id, live=True)


@router.post(
    "/api/projects/{project_id}/open",
    response_model=ProjectLoadOut,
    dependencies=[requires(Capability.MODEL_CONNECT)],
)
async def open_project(project_id: int) -> ProjectLoadOut:
    """Make this project current. Renders from its snapshot when one exists;
    only its first-ever open touches the DataServer."""
    return await _load_project(project_id, live=False)


@router.post(
    "/api/projects/{project_id}/refresh",
    response_model=ProjectLoadOut,
    dependencies=[requires(Capability.MODEL_CONNECT)],
)
async def refresh_project(project_id: int) -> ProjectLoadOut:
    """Browse the project's DataServer live and replace its snapshot."""
    return await _load_project(project_id, live=True)


@router.delete(
    "/api/projects/{project_id}",
    response_model=list[ProjectOut],
    dependencies=[requires(Capability.MODEL_CONNECT)],
)
async def delete_project(project_id: int) -> list[ProjectOut]:
    """Remove a project and its snapshot. Returns the remaining projects."""
    store = get_store()
    was_active = store.project is not None and store.project.id == project_id
    if not store.projects.delete(project_id):
        raise NotFoundError(f"no such project: {project_id}", project_id=project_id)
    if was_active:
        await store.unload()
    return await projects()


async def _load_project(project_id: int, *, live: bool) -> ProjectLoadOut:
    store = get_store()
    row = store.projects.get(project_id)
    if row is None:
        raise NotFoundError(f"no such project: {project_id}", project_id=project_id)
    error: str | None = None
    try:
        if live:
            await store.refresh_project(project_id)
        else:
            await store.open_project(project_id)
    except NotFoundError:
        raise
    except Exception as exc:  # reported in the response body, not raised
        error = f"{type(exc).__name__}: {exc}"
        log.error("project load failed", project=row.name, error=error)
    fresh = store.projects.get(project_id) or row
    return ProjectLoadOut(project=_out(fresh), ok=error is None, error=error)
