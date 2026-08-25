"""The list of commands this system is allowed to issue. Currently: none.

`COMMANDS` being empty is a load-bearing fact, not an oversight — `tools/check.py`
parses this file and fails if the literal stops being `{}`. Adding an entry
requires its own ADR stating what the command is, what must hold before it runs,
who may press it, and what the audit record contains (ADR-0011 §Việc phải làm).

The types are declared now so that `guard.py` and `audit.py` have something real
to be written against, and so that the shape of a command is settled while there
is no pressure to ship one.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from blackinterface.domain.models import Frozen
from blackinterface.domain.scope import ScopeKind


class CommandKind(StrEnum):
    """What a command does to the station, coarsely.

    Deliberately coarse: the distinction that matters for a guard is whether an
    operation moves primary plant, changes an operational marker, or only
    changes what the system pays attention to.
    """

    SWITCH = "switch"  # move a breaker or disconnector (C-09)
    TAP = "tap"  # raise/lower a transformer tap (C-09)
    TAGGING = "tagging"  # place or remove an operational tag (C-07)
    ALARM = "alarm"  # acknowledge / enable / disable an alarm


class Command(Frozen):
    """One permitted operation, and what it may be aimed at.

    `write_surface` names the OneATS method this would ultimately invoke. It is
    recorded here rather than at the call site so the registry alone answers
    "what can this system write", without reading any code.
    """

    id: str  # stable, e.g. "switch.open"
    kind: CommandKind
    write_surface: str  # e.g. "PosCtl" — see docs/30-integration §Bề mặt ghi
    scope_kinds: tuple[ScopeKind, ...]  # what it may target
    adr: str  # the ADR that opened it; no entry exists without one
    two_person: bool = False  # left undecided by ADR-0011, decided per command


#: Empty by decision (ADR-0011). Machine-enforced — see tools/check.py.
COMMANDS: Final[dict[str, Command]] = {}


def get(command_id: str) -> Command | None:
    """Look up a permitted command. Returns None for anything not opened."""
    return COMMANDS.get(command_id)
