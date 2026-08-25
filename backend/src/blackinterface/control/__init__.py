"""The single gated write path (AGENTS.md I1, ADR-0011).

Nothing outside this package may touch a OneATS write surface. Today nothing
inside it does either: `registry.COMMANDS` is empty and stays empty until an ADR
opens one command at a time. The system is, in practice, still read-only — what
changed is that the hole is drilled, so opening module C later is an addition
rather than a demolition.

`agent/` must never import this package. The agent prepares an operation and
explains it; a person presses the button. **Agent soạn phiếu, người ký.**
"""

from blackinterface.control.audit import AuditEntry, AuditSink
from blackinterface.control.guard import GuardVerdict, Refusal, RefusalCode, check_preconditions
from blackinterface.control.registry import COMMANDS, Command, CommandKind

__all__ = [
    "COMMANDS",
    "AuditEntry",
    "AuditSink",
    "Command",
    "CommandKind",
    "GuardVerdict",
    "Refusal",
    "RefusalCode",
    "check_preconditions",
]
