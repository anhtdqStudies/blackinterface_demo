"""Deciding what to do about a question. No model involved, and that is the rule.

This is where AGENTS.md I4 is actually enforced. Everything downstream of here
either reads the station or phrases what was read; the choice of *what to read*
is made in this module, by code, from the question text and the graph.

Two decisions live here, and neither is obvious enough to leave implicit.

**Which scope a question with no name in it is about.** "còn số đo thì sao?"
means whatever the conversation settled on — unless the operator has since
clicked something else on the diagram, in which case it means that. Both facts
are recorded per turn (`scope` and `asked_from`), so the rule is decidable
rather than guessed: if the pane has not moved since the last answer, the
conversation wins; if it has, the operator's hand wins.

**Whether "I could not find it" is an answer.** A question containing something
shaped like an identifier — `271`, `D03`, `BB21`, `D03.XCBR1` — that matches
nothing in this station must be told so. Widening to the pane's scope instead
would answer a question nobody asked, with numbers about somewhere else, and
read as though it were the answer. That failure is the reason for the shape test
below; it fails safe, because the worst case is being told a name is unknown
when it was only unusual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from blackinterface.agent.session import Conversation
from blackinterface.domain.scope import ScopeRef
from blackinterface.errors import InvalidInputError

#: Shapes that mean "this is the name of a piece of equipment", measured against
#: the naming OneATS actually uses on DEMO_SAS (2026-08-06):
#:   171, 271, 431      EVN circuit-breaker numbers (TT 44/2014/TT-BCT)
#:   271-1, 171-75      the disconnectors and earth switches under one
#:   D03, E07, BB21     bay and busbar ids
#:   AT1                transformer id
#:   D03.XCBR1          a device id, or any dotted path
#:   bay:D03            a scope ref somebody pasted
_IDENTIFIER = re.compile(
    r"""^(
        \d{3}(-\d{1,2})?              # 271, 271-1, 171-75
      | [A-Za-z]{1,3}\d{1,3}([.-].+)? # D03, BB21, AT1, D03.XCBR1
      | (station|vl|transformer|busbar|bay|device|point):.+
    )$""",
    re.VERBOSE,
)

_WORD = re.compile(r"[^\W_]+(?:[.:\-][^\W_]+)*", re.UNICODE)


@dataclass(frozen=True)
class Plan:
    """What to do with one question."""

    #: Text handed to the `resolve` tool. The whole question: the tool scans it
    #: for anything the station knows by name, which is more reliable than this
    #: module deciding in advance which words matter.
    query: str
    #: Where to answer about when the question names nothing.
    fallback: ScopeRef
    #: Why that fallback: `pane` (the operator is looking at it) or
    #: `conversation` (it is what we were talking about). Reported so an answer
    #: about an unexpected scope is explicable rather than mysterious.
    fallback_from: str
    #: Words in the question shaped like equipment names. If none of them
    #: resolves, say so instead of answering about `fallback` — and quote these
    #: back rather than the whole sentence, so the reply names what was not found.
    names: tuple[str, ...]

    @property
    def names_something(self) -> bool:
        return bool(self.names)


def plan(question: str, asked_from: ScopeRef, conversation: Conversation) -> Plan:
    settled = _settled_scope(conversation)
    moved = conversation.turns and conversation.turns[-1].asked_from != asked_from.ref
    if settled is not None and not moved:
        fallback, source = settled, "conversation"
    else:
        fallback, source = asked_from, "pane"

    return Plan(
        query=question,
        fallback=fallback,
        fallback_from=source,
        names=tuple(word for word in _WORD.findall(question) if _IDENTIFIER.match(word)),
    )


def _settled_scope(conversation: Conversation) -> ScopeRef | None:
    """The scope the conversation last landed on, if it is still readable.

    Parsed rather than trusted: the stored string came from this process, but a
    conversation outlives a project switch, and an unparseable one is a reason
    to start from the pane rather than to fail a question.
    """
    ref = conversation.scope
    if not ref:
        return None
    try:
        return ScopeRef.parse(ref)
    except InvalidInputError:
        return None
