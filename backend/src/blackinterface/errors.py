"""The error taxonomy. Every failure the API can report is one of these.

Why a closed set rather than raising whatever is convenient: an operator staring
at a substation console needs to tell three situations apart, and they are not
the same kind of problem.

  * the model is not loaded          -> the product is not ready
  * the source is unreachable        -> OneATS or the network is the problem
  * the model drifted from its pin   -> what you are looking at may be stale or
                                        wrong, and that is a safety issue (I7)

`code` is stable and machine-readable; the frontend switches on it. `message` is
for humans and may change.
"""

from __future__ import annotations

from typing import Any


class BlackInterfaceError(Exception):
    """Base for every error this application raises deliberately."""

    code = "internal_error"
    http_status = 500

    def __init__(self, message: str, **detail: Any) -> None:
        super().__init__(message)
        self.message = message
        self.detail: dict[str, Any] = detail

    def as_payload(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "detail": self.detail}}


class NotFoundError(BlackInterfaceError):
    code = "not_found"
    http_status = 404


class InvalidInputError(BlackInterfaceError):
    """The client sent something we understand enough to reject precisely."""

    code = "invalid_input"
    http_status = 400


class ConflictError(BlackInterfaceError):
    """The request collides with existing state, e.g. a duplicate project name."""

    code = "conflict"
    http_status = 409


class UnauthenticatedError(BlackInterfaceError):
    """Nobody is signed in (ADR-0017).

    Kept apart from `ForbiddenError` because the caller can do something about
    this one. A UI that cannot tell them apart either shows a login screen to
    somebody already signed in, or shows "not permitted" to somebody who only
    needed to sign in.
    """

    code = "unauthenticated"
    http_status = 401


class ForbiddenError(BlackInterfaceError):
    """The caller is known and lacks the capability this facet requires (ADR-0016).

    403 rather than 404: hiding the existence of a facet would mean the UI could
    not tell "you may not" from "it is broken", and an operator who cannot tell
    those apart escalates the wrong one.
    """

    code = "forbidden"
    http_status = 403


class ModelNotLoadedError(BlackInterfaceError):
    """No station model in memory yet, or the last load failed."""

    code = "model_not_loaded"
    http_status = 503


class SourceUnavailableError(BlackInterfaceError):
    """Could not reach or read the configured source (DataServer, fixture file)."""

    code = "source_unavailable"
    http_status = 502


class DriftError(BlackInterfaceError):
    """The source no longer matches what this release was pinned to.

    AGENTS.md I7: drift must surface as a system incident. Never fall back
    silently to a stale model.
    """

    code = "drift_detected"
    http_status = 409


class ConfigurationError(BlackInterfaceError):
    code = "configuration_error"
    http_status = 500
