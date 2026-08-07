"""What the tools found, said twice: once for a model, once for a person.

Both renderings come out of the same numbers in the same function, and that is
the point. If the prompt fed to the model and the fallback shown when there is
no model were built separately, they would drift, and the day the model was
unreachable the operator would get a differently-shaped answer to the one they
had learned to read.

The model's copy is `facts`: flat, unambiguous, no prose to imitate. The
person's copy is an i18n key plus arguments, not a sentence — the backend does
not know whether the reader wants Vietnamese or English, and a sentence baked in
here would be wrong in one of them (same reasoning as the limit codes in
`domain/evidence.py`).

Nothing here rounds, softens or omits. An undetermined position is counted as
undetermined all the way to the screen (I2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from blackinterface.api.schemas import ResolveOut, SummaryOut

#: i18n keys the frontend must be able to render. Listed here rather than
#: scattered through the code so the set the backend can emit is one list.
KEY_SUMMARY = "agent.answer.summary"
KEY_AMBIGUOUS = "agent.answer.ambiguous"
KEY_UNKNOWN = "agent.answer.unknown"
KEY_DENIED = "agent.answer.denied"

Params = dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class Brief:
    """One turn's findings, in both renderings."""

    facts: str
    key: str
    params: Params = field(default_factory=dict)


def for_summary(summary: SummaryOut, resolution: ResolveOut | None = None) -> Brief:
    """The ordinary case: a scope was identified and read."""
    closed = summary.switch_states.get("CLOSED", 0)
    opened = summary.switch_states.get("OPEN", 0)
    intermediate = summary.switch_states.get("INTERMEDIATE", 0)
    undetermined = summary.switch_states.get("UNDETERMINED", 0)
    devices = sum(summary.switch_states.values())

    lines = [
        f"scope: {summary.scope}" + (f" ({summary.label})" if summary.label else ""),
        f"bays: {', '.join(summary.bays) or 'none'}",
        f"switching devices: {devices}"
        f" (closed {closed}, open {opened},"
        f" intermediate {intermediate}, undetermined {undetermined})",
        f"conductors: {_pairs(summary.node_states) or 'none'}",
    ]
    if resolution is not None and resolution.scope:
        lines.insert(0, f"the question named: {resolution.query} -> {resolution.label or '-'}")
    lines.append(_readings(summary))
    lines.append(_issues(summary))
    lines.append(_limits(summary))

    return Brief(
        facts="\n".join(line for line in lines if line),
        key=KEY_SUMMARY,
        params={
            "label": summary.label or summary.scope,
            "scope": summary.scope,
            "devices": devices,
            "closed": closed,
            "opened": opened,
            "undetermined": undetermined + intermediate,
            "live": summary.node_states.get("LIVE", 0),
            "dead": summary.node_states.get("DEAD", 0),
            "unknown": summary.node_states.get("UNKNOWN", 0),
            "measurements": len(summary.measurements),
            "issues": len(summary.issues),
        },
    )


def for_ambiguity(resolution: ResolveOut) -> Brief:
    """Several things carry that name. Ask, do not choose (I8)."""
    options = ", ".join(f"{c.label or c.scope} ({c.scope})" for c in resolution.candidates)
    # The matched words, not the whole sentence: "«Lai Uyen» is two bays" is a
    # question somebody can answer; "«Lai Uyen thế nào?» is two bays" is not.
    named = resolution.candidates[0].matched if resolution.candidates else resolution.query
    return Brief(
        facts=f"the name {named!r} matches more than one thing: {options}. "
        f"Ask which one is meant. Do not pick one.",
        key=KEY_AMBIGUOUS,
        params={"query": named, "options": options, "count": len(resolution.candidates)},
    )


def for_unknown(query: str) -> Brief:
    """Nothing in this station carries that name."""
    return Brief(
        facts=f"nothing in this station is called {query!r}. Say so. Do not suggest what it "
        f"might have been.",
        key=KEY_UNKNOWN,
        params={"query": query},
    )


def for_denied(missing: str) -> Brief:
    """The caller may ask, but not about this."""
    return Brief(
        facts=f"this account lacks the permission {missing!r} and the question cannot be "
        f"answered for them. Say so plainly.",
        key=KEY_DENIED,
        params={"missing": missing},
    )


# ---------------------------------------------------------------- fragments


def _pairs(counts: dict[str, int]) -> str:
    return ", ".join(f"{name.lower()} {n}" for name, n in sorted(counts.items()) if n)


def _readings(summary: SummaryOut) -> str:
    if not summary.measurements:
        return "readings: none in this scope"
    lines = ["readings:"]
    for reading in summary.measurements:
        if reading.value is None:
            lines.append(f"  {reading.measurand}: unusable (quality {reading.quality.value})")
            continue
        # "?" means the DataServer publishes no engineering unit for this
        # quantity. Printing a guessed one is the trap in AGENTS.md section 7.
        unit = "" if reading.unit.value in ("", "?") else f" {reading.unit.value}"
        scale = " [scale not measured, do not name a unit]" if reading.unit.value == "?" else ""
        # Six significant figures. A float64 printed in full is seventeen digits
        # of instrument noise, and handing a model `65.21783447265625` invites
        # it to read the noise back out as precision. The exact value stays on
        # `SummaryOut.measurements`, where nothing is phrasing it.
        lines.append(
            f"  {reading.measurand} ({reading.quantity.value}): {reading.value:.6g}{unit}{scale}"
        )
    return "\n".join(lines)


def _issues(summary: SummaryOut) -> str:
    if not summary.issues:
        return "issues: none"
    lines = [f"issues: {len(summary.issues)}"]
    for issue in summary.issues[:8]:
        subject = f" [{issue.subject}]" if issue.subject else ""
        lines.append(f"  {issue.severity.value}: {issue.code}{subject} - {issue.message}")
    return "\n".join(lines)


def _limits(summary: SummaryOut) -> str:
    limits = summary.evidence.limits
    if not limits:
        return "caveats: none"
    return "caveats: " + ", ".join(f"{limit.code.value} x{limit.count}" for limit in limits)
