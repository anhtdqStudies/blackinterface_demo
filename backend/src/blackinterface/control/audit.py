"""Append-only record of every attempted operation (ADR-0011).

Attempted, not executed. A refused command is the more interesting record: it
says someone tried, when, against what, and what stopped them. A log that only
holds successes cannot answer the question asked after an incident.

There is no SQLite implementation here yet, and that is deliberate — a table
whose columns are guessed before the first command exists is a migration written
twice. What is fixed now is the *shape*: the entry, and the fact that a sink can
only append. When module C opens, the store-backed sink implements this Protocol
and nothing above it changes.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import Field

from blackinterface.control.guard import GuardVerdict
from blackinterface.domain.models import Frozen


class AuditEntry(Frozen):
    """One attempt on the station, with enough context to reconstruct it.

    `actor` is who pressed the button — never the agent. By ADR-0011 the agent
    cannot reach this module at all, so an entry naming one would mean the
    invariant had already been broken.
    """

    at: datetime
    actor: str
    command_id: str
    subject: str  # scope ref (ADR-0010)
    args: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    verdict: GuardVerdict
    executed: bool = False
    error: str | None = None
    release: str | None = None
    model_version: str | None = None


@runtime_checkable
class AuditSink(Protocol):
    """Somewhere entries go and never come back out changed.

    No update, no delete, no id to address an existing row by — the interface
    itself is the guarantee, so a caller cannot rewrite history even by mistake.
    """

    def append(self, entry: AuditEntry) -> None: ...

    def recent(self, limit: int = 100) -> Sequence[AuditEntry]: ...


class NullAuditSink:
    """Accepts and discards. The only sink while `COMMANDS` is empty.

    It exists so the call sites in `control/` are written against a real object
    rather than against `None`, and so a test can prove the guard tries to
    record a refusal before anything is wired to storage.
    """

    def __init__(self) -> None:
        self._count = 0

    def append(self, entry: AuditEntry) -> None:
        self._count += 1

    def recent(self, limit: int = 100) -> Sequence[AuditEntry]:
        return ()

    @property
    def count(self) -> int:
        return self._count
