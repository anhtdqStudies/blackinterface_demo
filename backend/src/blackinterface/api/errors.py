"""Map exceptions to one consistent JSON error body.

Every failure looks the same on the wire:

    {"error": {"code": "...", "message": "...", "detail": {...}}}

The frontend switches on `code`. Because the shape is uniform, the generated
TypeScript types cover error handling too — there is no second, undocumented
error format to discover at 2 a.m.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from blackinterface.errors import BlackInterfaceError
from blackinterface.logs import get_logger

log = get_logger(__name__)


async def handle_known(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, BlackInterfaceError)
    log.warning(
        "request failed",
        code=exc.code,
        path=request.url.path,
        message=exc.message,
        **exc.detail,
    )
    return JSONResponse(status_code=exc.http_status, content=exc.as_payload())


async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """Anything we did not anticipate. Logged with a traceback, reported plainly.

    The message deliberately does not leak internals to the client, but the log
    carries the exception so the incident is diagnosable.
    """
    log.exception("unhandled error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Unexpected server error. See the application log.",
                "detail": {},
            }
        },
    )


def install(app: FastAPI) -> None:
    app.add_exception_handler(BlackInterfaceError, handle_known)
    app.add_exception_handler(Exception, handle_unexpected)
