"""Typed Domain API — deterministic, LLM-free (AGENTS.md I4, I5).

The frontend talks to these endpoints directly. BlackCore, when it exists, will
call the same ones with the same rights: no private path, no elevated access.

This module composes the application and does nothing else. Endpoints live in
`routers/`, response shapes in `schemas.py`, domain-to-wire translation in
`mappers.py`, and the store in `deps.py`. Router registration order below is the
order paths appear in `backend/openapi.json` — keep it.

Read-only with respect to OneATS. The one place a write could ever live is
`control/`, whose registry is empty (I1, ADR-0011).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from blackinterface.api import accounts, deps
from blackinterface.api import errors as error_handlers
from blackinterface.api.routers import (
    auth,
    diagram,
    health,
    issues,
    live,
    me,
    projects,
    station,
    summary,
)
from blackinterface.logs import configure as configure_logging
from blackinterface.logs import get_logger

log = get_logger(__name__)

settings = deps.settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level, settings.log_json)
    log.info(
        "starting",
        source=settings.source,
        db=str(settings.db_path),
        frontend=str(settings.frontend_dir) if settings.frontend_dir else None,
    )
    # Read through deps rather than closing over them: a test swaps the store
    # before entering the TestClient, and startup has to see the swap.
    deps.get_database().migrate()
    # Accounts, before anything else can need one. Seeding only touches a
    # database with no users at all, so it cannot resurrect a deleted account
    # (ADR-0017); the warning about default passwords is repeated every start,
    # because one that fires only at install stops being seen when it matters.
    accounts.seed_default_accounts(settings)
    accounts.warn_about_seeded_passwords()
    # Reopen the last project from its snapshot, else fall back to BI_SOURCE.
    # A failed load must not take the process down: /api/health has to stay
    # answerable so an operator can see *why* nothing is showing.
    await deps.get_store().startup()
    yield
    await deps.get_store().shutdown()
    deps.get_database().close()


app = FastAPI(
    title="Black Interface — Domain API",
    version="0.1.0",
    summary="Read-only station model from OneATS DataServer",
    lifespan=lifespan,
)
error_handlers.install(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(projects.router)
app.include_router(station.router)
app.include_router(issues.router)
app.include_router(live.router)
app.include_router(summary.router)
app.include_router(diagram.router)


# ------------------------------------------------------------------- frontend
# Serves frontend/dist when the SPA has been built. See ADR-0009: there is no
# fallback UI, because a stale one is more dangerous than none.
_frontend = settings.frontend_dir
if _frontend is not None:
    if (_frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_frontend / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        assert _frontend is not None
        return FileResponse(_frontend / "index.html")
