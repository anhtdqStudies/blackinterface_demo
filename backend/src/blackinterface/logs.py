"""Structured logging setup. Call `configure()` once, at process start.

Human-readable while developing, JSON at the station (`BI_LOG_JSON=true`) so the
log can be shipped or grepped without a parser.

Every log line about station data should carry the identifiers that make it
traceable — `bay_id`, `device_id`, `source_ref`, `model_version` — because in an
incident the log is evidence, and evidence without provenance is worthless (I3).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_configured = False


def configure(level: str = "INFO", json_output: bool = False) -> None:
    """Idempotent: safe to call from both the app and the test suite."""
    global _configured
    if _configured:
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

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
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
