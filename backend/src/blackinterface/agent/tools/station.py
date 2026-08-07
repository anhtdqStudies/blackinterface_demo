"""The two tools the thin slice ships: name a thing, then read it.

Two is not a placeholder count. They are the two halves of every question in
`document/@Station_UseCases 1.xlsx`: *which part of the station* and *how is it
doing*. Adding use cases should add scopes and filters, not tools — if a new use
case needs a new tool, the addressing model is wrong (AGENTS.md I8). Starting
with two is how that claim gets tested while it is still cheap to be wrong about.

Neither tool computes anything of its own. `summary` calls exactly the function
behind `GET /api/summary`, under the permissions of whoever asked (I5): the
agent uses the API the interface uses, with no private path and no wider rights.
"""

from __future__ import annotations

from blackinterface import __version__
from blackinterface.agent import resolve as resolver
from blackinterface.agent.tools.registry import (
    Tool,
    ToolArgs,
    ToolContext,
    ToolResult,
    register,
)
from blackinterface.api.schemas import ResolveOut, ScopeCandidateOut
from blackinterface.api.summary import build_summary, source_kind
from blackinterface.domain.authz import Capability
from blackinterface.domain.evidence import EvidenceBuilder, EvidenceRecord, Source
from blackinterface.domain.models import StationGraph
from blackinterface.domain.scope import ScopeRef
from blackinterface.errors import InvalidInputError

RESOLVE = "resolve"
SUMMARY = "summary"


def run_resolve(ctx: ToolContext, args: ToolArgs) -> ToolResult:
    """Text -> scope ref, or a list of what it could have been.

    Carries an evidence record even though it reads no points, and the record is
    not ceremony: the names it matched against came from one model version of one
    station, and "271 is D03's breaker" stops being true the moment somebody
    loads a different station. Provenance is the whole content of this answer.
    """
    query = _text(args, "query")
    graph = ctx.store.graph
    match = resolver.resolve(graph, query)
    if not match.found:
        match = resolver.find_in_text(graph, query)

    chosen = match.scope
    payload = ResolveOut(
        query=query,
        scope=chosen.ref if chosen is not None else None,
        label=chosen.label if chosen is not None else "",
        ambiguous=match.ambiguous,
        candidates=[
            ScopeCandidateOut(
                scope=c.ref,
                kind=c.kind.value,
                label=c.label,
                tier=c.tier.name.lower(),
                matched=c.matched,
            )
            for c in match.candidates
        ],
    )
    subject = chosen if chosen is not None else ScopeRef.station()
    return ToolResult(payload=payload, evidence=_evidence(RESOLVE, subject, graph, ctx, query))


def run_summary(ctx: ToolContext, args: ToolArgs) -> ToolResult:
    """How one scope is doing. The facet, called directly (I5)."""
    scope = _text(args, "scope")
    out = build_summary(ctx.store, scope, actor=ctx.principal.user)
    return ToolResult(payload=out, evidence=out.evidence)


def _text(args: ToolArgs, key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"tool argument {key!r} must be a non-empty string", arg=key)
    return value.strip()


def _evidence(
    tool: str, subject: ScopeRef, graph: StationGraph, ctx: ToolContext, query: str
) -> EvidenceRecord:
    builder = EvidenceBuilder(
        tool,
        subject,
        source=Source(
            kind=source_kind(graph.source),
            endpoint=graph.source or None,
            catalog_snapshot=graph.model_version,
        ),
        actor=ctx.principal.user or None,
        args={"query": query},
        release=__version__,
        model_version=graph.model_version,
    )
    return builder.build()


register(
    Tool(
        name=RESOLVE,
        description=(
            "Turn what the operator called something - an EVN number like 271, a bay "
            "name, an id - into a scope reference. Returns every match; several "
            "matches means ask which one."
        ),
        requires=Capability.STATION_READ,
        run=run_resolve,
    )
)

register(
    Tool(
        name=SUMMARY,
        description=(
            "Read the present state of one scope: switch positions, which conductors "
            "are live, analog readings, and open issues, with the evidence behind them."
        ),
        requires=Capability.STATION_READ,
        run=run_summary,
    )
)
