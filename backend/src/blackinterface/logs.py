"""Structured logging setup. Call `configure()` once, at process start.

Human-readable while developing, JSON at the station (`BI_LOG_JSON=true`) so the
log can be shipped or grepped without a parser.

Every log line about station data should carry the identifiers that make it
traceable — `bay_id`, `device_id`, `source_ref`, `model_version` — because in an
incident the log is evidence, and evidence without provenance is worthless (I3).

A log nobody can read is not a log. `basicConfig` opens the root logger, which
means third-party INFO comes out alongside ours, and asyncua's is loud enough to
drown the process — so `configure()` also decides how much of it to let through
and where it goes. See `_route_opcua`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog

#: Parent of every logger asyncua creates (`asyncua.common.subscription`,
#: `asyncua.client.ua_client.UASocketProtocol`, and the rest). Filtering here
#: catches all of them without naming any.
OPCUA_LOGGER = "asyncua"

_configured = False


def _level(name: str) -> int:
    value = getattr(logging, name.upper(), logging.INFO)
    return value if isinstance(value, int) else logging.INFO


def _route_opcua(level: str, path: Path | None) -> None:
    """Decide how much asyncua says, and where.

    Its publish callback logs one line per notification at INFO — on a station
    whose analog points move constantly that is a multi-kilobyte line twice a
    second, and it buries everything this application has to say. The level is
    a knob rather than a hard-coded WARNING because the trace is genuinely the
    right tool when the link itself is what is wrong.

    A file, when one is named, takes the traffic *instead of* the console
    (`propagate = False`): the point of asking for a file is to get it out of
    the way, so leaving it in both places would defeat the request.
    """
    logger = logging.getLogger(OPCUA_LOGGER)
    logger.setLevel(_level(level))

    # Idempotence: `configure()` may be re-entered by a test that reset the
    # module flag, and handlers accumulate silently if nobody clears them.
    for handler in [h for h in logger.handlers if getattr(h, "_blackinterface", False)]:
        logger.removeHandler(handler)
        handler.close()

    if path is None:
        logger.propagate = True
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler._blackinterface = True  # type: ignore[attr-defined]  # ours to remove
    logger.addHandler(handler)
    logger.propagate = False


def configure(
    level: str = "INFO",
    json_output: bool = False,
    *,
    opcua_level: str = "WARNING",
    opcua_file: Path | None = None,
) -> None:
    """Idempotent: safe to call from both the app and the test suite."""
    global _configured
    if _configured:
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=_level(level),
    )
    _route_opcua(opcua_level, opcua_file)

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(_level(level)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
