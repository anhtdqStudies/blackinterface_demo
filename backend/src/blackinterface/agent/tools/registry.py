"""What the agent is allowed to do, and the gate every use goes through.

One registry, read-only, and the read-only part is structural rather than
promised (I1, ADR-0011 section 3):

  * `agent/` cannot import `control/` or `integration/` — `tools/check.py`
    section 2 fails the build if it does. So a tool here has nothing to write
    *with*; it would have to go out through `api/`, which offers no write path.
  * A tool declares the capability it needs, and that capability must be one of
    `READ_ONLY`. Anything that changes something — acknowledging an alarm,
    drafting an operation, editing the model, exporting a report off the
    machine — is absent from that set, and `register()` refuses the tool.

The second is the one worth having even though the first already holds. The day
Module C opens the write path, `control.draft` becomes a capability some accounts
legitimately hold, and the agent borrows the caller's capabilities (ADR-0016
section 5). Without this list, that day would silently hand the agent a write
tool through a permission model working exactly as designed.

Every tool returns `(payload, EvidenceRecord)` — the payload is typed and the
evidence is built by the tool, never phrased by a model (I3). The registry keeps
them together so nothing downstream can deliver one without the other.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from blackinterface.api.source import StationStore
from blackinterface.domain.authz import Capability, Principal
from blackinterface.domain.evidence import EvidenceRecord
from blackinterface.errors import ForbiddenError, InvalidInputError
from blackinterface.logs import get_logger

log = get_logger(__name__)

#: The capabilities a tool may demand. Every one of them is a *read*.
#:
#: Note what is missing and why, because the omissions are the rule:
#: `alarm.ack`, `control.draft`, `control.sign`, `knowledge.write`, `model.edit`,
#: `model.connect`, `model.publish`, `account.manage` all change something.
#: `report.export` reads, but sends the result off the machine, which is an
#: effect on the world in the same way — the agent may compose a report, a
#: person sends it.
READ_ONLY: frozenset[Capability] = frozenset(
    {
        Capability.STATION_READ,
        Capability.ALARM_READ,
        Capability.EVENT_READ,
        Capability.TREND_READ,
        Capability.REPORT_READ,
        Capability.KNOWLEDGE_READ,
        Capability.PROTECTION_READ,
        Capability.BINDING_READ,
        Capability.AUDIT_READ,
    }
)

#: Arguments as they arrive from a plan. Strings and numbers only: a tool
#: argument that could be a nested object is a tool argument nobody can log,
#: replay or put in an evidence record.
ToolArgs = Mapping[str, str | int | float | bool | None]


@dataclass(frozen=True)
class ToolContext:
    """Everything a tool may reach. Nothing global, so a test can build one.

    `principal` is the person who asked, never the agent. The agent has no
    identity and no permissions of its own — it runs as whoever is typing
    (ADR-0016 section 5), which is why the same question gets a different answer
    for an operator and for an admin.
    """

    store: StationStore
    principal: Principal


@dataclass(frozen=True)
class ToolResult:
    """A typed answer and the record of how far it can be trusted."""

    payload: BaseModel
    evidence: EvidenceRecord


@dataclass(frozen=True)
class Tool:
    """One thing the agent can do."""

    name: str
    #: What the agent would be told this tool is for. Kept next to the code
    #: rather than in a prompt file so it cannot drift from what runs.
    description: str
    requires: Capability
    run: Callable[[ToolContext, ToolArgs], ToolResult]


#: Name -> tool. Populated by `register()` at import of `agent.tools`.
TOOLS: dict[str, Tool] = {}


class WriteToolError(RuntimeError):
    """Someone tried to register a tool that could change something (I1).

    A plain `RuntimeError` and raised at import, not at call: a write tool must
    not exist long enough to be reachable, and a process that starts and then
    refuses one request has already shipped it.
    """


def register(tool: Tool) -> Tool:
    if tool.requires not in READ_ONLY:
        raise WriteToolError(
            f"tool {tool.name!r} demands {tool.requires.value!r}, which is not a read. "
            f"The agent never holds a write tool (AGENTS.md I1, ADR-0011 section 3)."
        )
    if tool.name in TOOLS:
        raise RuntimeError(f"duplicate tool name: {tool.name!r}")
    TOOLS[tool.name] = tool
    return tool


def call(name: str, args: ToolArgs, ctx: ToolContext) -> ToolResult:
    """Run one tool as the caller. Refuses rather than degrades.

    A capability the caller lacks is a 403 here, not a quieter answer. The
    alternative — omitting the part they may not see — produces an answer that
    reads as complete and is not, which is worse than being told no.
    """
    tool = TOOLS.get(name)
    if tool is None:
        raise InvalidInputError(f"no such tool: {name!r}", known=sorted(TOOLS))
    if not ctx.principal.can(tool.requires):
        log.warning(
            "tool denied",
            tool=tool.name,
            user=ctx.principal.user,
            missing=tool.requires.value,
        )
        raise ForbiddenError(
            "this account may not use that part of the assistant",
            tool=tool.name,
            missing=[tool.requires.value],
        )
    return tool.run(ctx, args)


def catalogue(principal: Principal) -> tuple[Tool, ...]:
    """The tools this caller could actually use, in a stable order."""
    return tuple(t for _, t in sorted(TOOLS.items()) if principal.can(t.requires))
