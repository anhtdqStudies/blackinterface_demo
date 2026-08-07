"""Preconditions. Nothing gets issued without passing through here (ADR-0011).

This module has two jobs and they are the same code:

  * the gate in front of every command in `registry.COMMANDS`
  * the read-only answer to use case **C-01 Interlock Check** — *"can 271 be
    opened right now, and if not, why not"*

Because the second is pure reading, it can be built and proved long before the
first exists. That is the point: the hard half of module C gets verified while
the write path is still shut.

Two rules shape everything below.

**Refusal is the default.** A precondition that cannot be evaluated is not a
precondition that passed. Missing data, bad quality, an unknown device — each
produces a refusal, never a shrug. This is I2 applied to an action instead of to
a sentence.

**Refusals are codes.** The UI translates them (ADR-0014) and the agent explains
them in the operator's own words (I3/I4); prose here would be wrong in both.
"""

from __future__ import annotations

from enum import StrEnum

from blackinterface.domain.models import Frozen, StationGraph, SwitchState
from blackinterface.domain.scope import ScopeKind, ScopeLike, as_scope


class RefusalCode(StrEnum):
    """Why an operation is not permitted right now."""

    UNKNOWN_COMMAND = "unknown_command"  # not in the registry — the normal case today
    UNKNOWN_TARGET = "unknown_target"  # the scope names nothing in this station
    WRONG_SCOPE_KIND = "wrong_scope_kind"  # e.g. a switch command aimed at a bay
    POSITION_UNKNOWN = "position_unknown"  # quality is not GOOD, so nothing may be asserted
    POSITION_INTERMEDIATE = "position_intermediate"  # mechanism between states
    ALREADY_IN_STATE = "already_in_state"  # asking for what is already true
    TAGGED = "tagged"  # an operational tag forbids it (C-07/C-08)
    NOT_LOCAL_AUTHORITY = "not_local_authority"  # control is elsewhere (C-02)
    INTERLOCK = "interlock"  # an electrical interlock blocks it
    NOT_EVALUABLE = "not_evaluable"  # we do not know enough to permit it


class Refusal(Frozen):
    """One reason an operation is blocked, aimed at a specific subject."""

    code: RefusalCode
    subject: str  # scope ref
    detail: str = ""  # ids and values only; never a translated sentence


class GuardVerdict(Frozen):
    """The answer to "may this happen": permitted, or a list of reasons why not.

    `checked` names the preconditions actually evaluated, so a caller can tell
    "nothing blocks it" apart from "nothing was looked at".
    """

    permitted: bool
    subject: str
    refusals: tuple[Refusal, ...] = ()
    checked: tuple[str, ...] = ()


def check_preconditions(
    graph: StationGraph,
    command_id: str,
    target: ScopeLike,
    *,
    to_state: SwitchState | None = None,
) -> GuardVerdict:
    """Evaluate everything we can decide about an operation, and refuse the rest.

    Today this always refuses at the first step, because `registry.COMMANDS` is
    empty — which is exactly the behaviour ADR-0011 asks for and is worth having
    a test on. The checks below the registry lookup are reached by C-01, which
    asks the same questions without naming a command.
    """
    from blackinterface.control.registry import get as get_command

    scope = as_scope(target)
    command = get_command(command_id)
    if command is None:
        return GuardVerdict(
            permitted=False,
            subject=scope.ref,
            refusals=(
                Refusal(code=RefusalCode.UNKNOWN_COMMAND, subject=scope.ref, detail=command_id),
            ),
            checked=("registry",),
        )
    if scope.kind not in command.scope_kinds:
        return GuardVerdict(
            permitted=False,
            subject=scope.ref,
            refusals=(
                Refusal(
                    code=RefusalCode.WRONG_SCOPE_KIND, subject=scope.ref, detail=scope.kind.value
                ),
            ),
            checked=("registry", "scope_kind"),
        )
    return switching_verdict(graph, scope, to_state=to_state)


def switching_verdict(
    graph: StationGraph,
    target: ScopeLike,
    *,
    to_state: SwitchState | None = None,
) -> GuardVerdict:
    """C-01: what stands in the way of moving this device, command aside.

    Read-only and deterministic, so it answers an operator's question and gates
    an operation with the same code. The interlock rules themselves are not here
    yet — and their absence is reported (`NOT_EVALUABLE`) rather than treated as
    "no interlock". An unasked question must never read as a cleared one.
    """
    scope = as_scope(target)
    refusals: list[Refusal] = []
    checked = ["target", "quality"]

    if scope.kind is not ScopeKind.DEVICE:
        return GuardVerdict(
            permitted=False,
            subject=scope.ref,
            refusals=(
                Refusal(
                    code=RefusalCode.WRONG_SCOPE_KIND, subject=scope.ref, detail=scope.kind.value
                ),
            ),
            checked=("target",),
        )

    device = graph.device(scope.id)
    if device is None:
        return GuardVerdict(
            permitted=False,
            subject=scope.ref,
            refusals=(Refusal(code=RefusalCode.UNKNOWN_TARGET, subject=scope.ref),),
            checked=("target",),
        )

    state = device.state
    if state is SwitchState.UNDETERMINED:
        refusals.append(
            Refusal(
                code=RefusalCode.POSITION_UNKNOWN,
                subject=scope.ref,
                detail=device.position.quality.value,
            )
        )
    elif state is SwitchState.INTERMEDIATE:
        refusals.append(Refusal(code=RefusalCode.POSITION_INTERMEDIATE, subject=scope.ref))
    elif to_state is not None and state is to_state:
        checked.append("target_state")
        refusals.append(
            Refusal(code=RefusalCode.ALREADY_IN_STATE, subject=scope.ref, detail=state.value)
        )

    # Tagging (C-08), control authority (C-02) and the interlock rules proper
    # are not modelled yet. Saying so is the honest verdict; silence here would
    # read as "checked, and clear".
    refusals.append(
        Refusal(
            code=RefusalCode.NOT_EVALUABLE,
            subject=scope.ref,
            detail="tagging,authority,interlock",
        )
    )
    return GuardVerdict(
        permitted=False,
        subject=scope.ref,
        refusals=tuple(refusals),
        checked=tuple(checked),
    )
