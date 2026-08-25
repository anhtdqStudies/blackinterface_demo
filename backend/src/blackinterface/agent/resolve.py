"""Turning what a person said into a scope ref — deterministically (I8).

An operator says "271", or "Bến Cát", or "ngăn D03". The station has a name for
each of those and the graph knows it. This module does the lookup; **the model
never does** (AGENTS.md I8, ADR-0005). That rule is not caution about
hallucination in general — it is about one specific failure. A model that half
remembers the station will answer a question about D03 with numbers from D04,
fluently, and nothing downstream can tell.

So: a match is found, or it is not. Several matches are reported as several, and
the caller asks which one. There is no "closest" and no "probably".

Matching runs in tiers, strongest first, and stops at the first tier that finds
anything. A tier is a claim about how strong the evidence is, and mixing tiers
would let a display-name near-miss dilute an exact id:

    REF          "bay:D03"     already a scope ref, and it exists
    ID           "d03", "at1"  an id in the model
    DESIGNATION  "271", "271-1" the EVN number painted on the equipment
    NAME         "Bến Cát"     a display name, and the only ambiguous tier

Ambiguity is real and must survive: `Lai Uyen` is the name of both E01 and E02
on DEMO_SAS. Two bays, one name, and the difference between them is which line
is about to be switched.
"""

from __future__ import annotations

import re
import unicodedata
from enum import IntEnum

from blackinterface.domain.models import StationGraph
from blackinterface.domain.scope import ScopeRef, exists
from blackinterface.errors import InvalidInputError

#: A word as it might name something: letters, digits, and the separators that
#: appear *inside* station identifiers — `271-1`, `D03.XCBR1`, `bay:D03`.
_WORD = re.compile(r"[^\W_]+(?:[.:\-][^\W_]+)*", re.UNICODE)

#: How many words a name may span. "AT1 Incoming" is two; nothing in the model
#: measured so far is longer than three, and a wider window only costs lookups
#: against phrases no station uses.
MAX_PHRASE_WORDS = 4


class Tier(IntEnum):
    """How strong a match is. Higher wins; ties within a tier are ambiguity."""

    NAME = 1
    DESIGNATION = 2
    ID = 3
    REF = 4


class Candidate(ScopeRef):
    """One thing the query could mean, with the reason it matched.

    A `ScopeRef` subclass rather than a wrapper so it can be passed anywhere a
    scope is expected without unwrapping — and so the reason travels with it,
    which is what makes "did you mean E01 or E02" answerable.
    """

    label: str = ""
    tier: Tier = Tier.NAME
    matched: str = ""


class Match:
    """The outcome of one lookup: nothing, one thing, or an ambiguity.

    Deliberately not an exception on the ambiguous case. "Which of these two"
    is an answer, and a useful one — the caller turns it into a question back to
    the operator rather than into a failure.
    """

    __slots__ = ("candidates", "query")

    def __init__(self, query: str, candidates: tuple[Candidate, ...]) -> None:
        self.query = query
        self.candidates = candidates

    @property
    def scope(self) -> Candidate | None:
        """The one match, or None when there were none or several."""
        return self.candidates[0] if len(self.candidates) == 1 else None

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1

    @property
    def found(self) -> bool:
        return bool(self.candidates)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Match({self.query!r}, {[c.ref for c in self.candidates]})"


def fold(text: str) -> str:
    """Compare-ready form: lowercase, unaccented, single-spaced.

    Operators type "Bến Cát"; the DataServer stores "Ben Cat" (measured
    2026-08-06 — OneATS holds display names unaccented). Neither side should
    have to know that about the other, so both are folded before comparing.
    """
    lowered = text.strip().lower().replace("đ", "d")
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", lowered) if not unicodedata.combining(ch)
    )
    return " ".join(stripped.split())


def resolve(graph: StationGraph, query: str) -> Match:
    """What this text names in this station. Never guesses (I8)."""
    folded = fold(query)
    if not folded:
        return Match(query, ())

    for tier in sorted(Tier, reverse=True):
        found = _by_tier(graph, tier, query, folded)
        if found:
            return Match(query, found)
    return Match(query, ())


def find_in_text(graph: StationGraph, text: str) -> Match:
    """The strongest thing named anywhere in a sentence.

    "trạng thái của 271 thế nào?" contains one name and a lot of grammar. Every
    window of up to `MAX_PHRASE_WORDS` consecutive words is tried; the strongest
    tier wins, and among equals the longest phrase does — "AT1 Incoming" should
    beat the "AT1" inside it.
    """
    words = _WORD.findall(text)
    best = Match(text, ())
    best_key = (0, 0)
    for size in range(1, MAX_PHRASE_WORDS + 1):
        for start in range(len(words) - size + 1):
            phrase = " ".join(words[start : start + size])
            match = resolve(graph, phrase)
            if not match.found:
                continue
            key = (int(match.candidates[0].tier), size)
            if key > best_key:
                best, best_key = match, key
    return best


# ----------------------------------------------------------------------- tiers


def _by_tier(graph: StationGraph, tier: Tier, query: str, folded: str) -> tuple[Candidate, ...]:
    match tier:
        case Tier.REF:
            return _as_ref(graph, query, tier)
        case Tier.ID:
            return _by_id(graph, folded, tier)
        case Tier.DESIGNATION:
            return tuple(
                _candidate(ScopeRef.device(d.id), d.name, tier, query)
                for d in graph.devices
                if d.name and fold(d.name) == folded
            )
        case Tier.NAME:
            return _by_name(graph, folded, tier)


def _as_ref(graph: StationGraph, query: str, tier: Tier) -> tuple[Candidate, ...]:
    """Already a scope ref — accepted only if the station actually has it.

    A well-formed ref for something absent is not a match. Returning it anyway
    would hand the next tool a scope that fails at the door, one step further
    from the mistake.
    """
    try:
        ref = ScopeRef.parse(query.strip())
    except InvalidInputError:
        return ()
    if not exists(graph, ref):
        return ()
    return (_candidate(ref, _label_of(graph, ref), tier, query),)


def _by_id(graph: StationGraph, folded: str, tier: Tier) -> tuple[Candidate, ...]:
    """An id, written bare. `D03`, `at1`, `BB21`, `220kV`, `D03.XCBR1`.

    Ids are unique within their kind by construction, and across kinds by the
    naming OneATS uses, so this tier is not expected to be ambiguous — but it is
    collected as a list anyway, because "not expected to" is not a guarantee
    about a station nobody has connected to yet.
    """
    found: list[Candidate] = []
    for level in graph.voltage_levels:
        if fold(level) == folded:
            found.append(_candidate(ScopeRef.voltage_level(level), level, tier, level))
    for transformer in graph.transformers:
        if fold(transformer.id) == folded:
            found.append(
                _candidate(
                    ScopeRef.transformer(transformer.id), transformer.name, tier, transformer.id
                )
            )
    for busbar in graph.busbars:
        if fold(busbar.id) == folded:
            found.append(_candidate(ScopeRef.busbar(busbar.id), busbar.name, tier, busbar.id))
    for bay in graph.bays:
        if fold(bay.id) == folded:
            found.append(_candidate(ScopeRef.bay(bay.id), bay.name, tier, bay.id))
    for device in graph.devices:
        if fold(device.id) == folded:
            found.append(_candidate(ScopeRef.device(device.id), device.name, tier, device.id))
    return tuple(found)


def _by_name(graph: StationGraph, folded: str, tier: Tier) -> tuple[Candidate, ...]:
    """A display name. The tier where two answers is the normal case."""
    found: list[Candidate] = []
    for transformer in graph.transformers:
        if transformer.name and fold(transformer.name) == folded:
            found.append(
                _candidate(
                    ScopeRef.transformer(transformer.id), transformer.name, tier, transformer.name
                )
            )
    for busbar in graph.busbars:
        if busbar.name and fold(busbar.name) == folded:
            found.append(_candidate(ScopeRef.busbar(busbar.id), busbar.name, tier, busbar.name))
    for bay in graph.bays:
        if bay.name and fold(bay.name) == folded:
            found.append(_candidate(ScopeRef.bay(bay.id), bay.name, tier, bay.name))
    return tuple(found)


def _candidate(ref: ScopeRef, label: str, tier: Tier, matched: str) -> Candidate:
    return Candidate(kind=ref.kind, id=ref.id, label=label, tier=tier, matched=matched)


def _label_of(graph: StationGraph, ref: ScopeRef) -> str:
    for bay in graph.bays:
        if ScopeRef.bay(bay.id) == ref:
            return bay.name
    for device in graph.devices:
        if ScopeRef.device(device.id) == ref:
            return device.name
    for busbar in graph.busbars:
        if ScopeRef.busbar(busbar.id) == ref:
            return busbar.name
    for transformer in graph.transformers:
        if ScopeRef.transformer(transformer.id) == ref:
            return transformer.name
    return ref.id
