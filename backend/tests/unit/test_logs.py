"""asyncua's chatter must not bury ours.

The library logs one line per publish at INFO. With a 500 ms publishing
interval and analog points that never sit still, that is a multi-kilobyte line
twice a second on the same stream the application writes to — which makes the
application's log unreadable in practice, so this is a correctness concern
about the log and not a matter of taste.

These tests drive `_route_opcua` directly. `configure()` is idempotent by
design and the process has usually configured itself already by the time any
test runs, so calling it here would assert nothing.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from blackinterface.config import Settings
from blackinterface.logs import OPCUA_LOGGER, _route_opcua


@pytest.fixture(autouse=True)
def restore_opcua_logger():
    """Leave the logger exactly as found: it is process-global state."""
    logger = logging.getLogger(OPCUA_LOGGER)
    before = (logger.level, logger.propagate, list(logger.handlers))
    yield
    _route_opcua("WARNING", None)  # drops handlers this module added
    logger.setLevel(before[0])
    logger.propagate = before[1]
    logger.handlers = before[2]


def test_the_publish_line_is_off_by_default() -> None:
    """The default has to be silent, because nobody edits config to stop noise
    they have not met yet — they just stop reading the log."""
    assert Settings().log_opcua_level == "WARNING"

    _route_opcua(Settings().log_opcua_level, None)
    logger = logging.getLogger(OPCUA_LOGGER)

    # The real call site: asyncua/common/subscription.py logs the PublishResult
    # at INFO from a child of this logger.
    assert not logging.getLogger(f"{OPCUA_LOGGER}.common.subscription").isEnabledFor(logging.INFO)
    assert logger.isEnabledFor(logging.WARNING), "a link that fails must still say so"


def test_turning_it_back_on_works() -> None:
    """Off by default is only defensible if the trace is one variable away —
    when the link itself is what is wrong, this is the tool you want."""
    _route_opcua("DEBUG", None)

    assert logging.getLogger(f"{OPCUA_LOGGER}.common.subscription").isEnabledFor(logging.INFO)


def test_a_file_takes_the_traffic_instead_of_the_console(tmp_path: Path) -> None:
    """Instead of, not as well as. Asking for a file means asking for it out of
    the way; duplicating it to stdout would answer the wrong question."""
    path = tmp_path / "logs" / "opcua.log"  # note: the directory does not exist yet
    _route_opcua("INFO", path)

    logger = logging.getLogger(f"{OPCUA_LOGGER}.common.subscription")
    logger.info("Publish callback called with result: %s", "PublishResult(...)")
    logging.getLogger(OPCUA_LOGGER).handlers[0].flush()

    assert path.exists(), "the parent directory should have been created"
    assert "Publish callback called" in path.read_text(encoding="utf-8")
    assert not logging.getLogger(OPCUA_LOGGER).propagate, "must not also reach the root handler"


def test_switching_back_to_the_console_releases_the_file(tmp_path: Path) -> None:
    """Handlers accumulate silently. One reconfiguration must not leave two
    sinks writing the same lines to a file nobody is watching."""
    _route_opcua("INFO", tmp_path / "opcua.log")
    _route_opcua("WARNING", None)

    logger = logging.getLogger(OPCUA_LOGGER)
    assert logger.handlers == []
    assert logger.propagate


def test_an_unknown_level_name_does_not_take_the_process_down() -> None:
    """A typo in an environment variable is a bad log, not a dead station."""
    _route_opcua("VERBOSE", None)

    assert logging.getLogger(OPCUA_LOGGER).level == logging.INFO
