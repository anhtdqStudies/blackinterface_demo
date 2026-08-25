"""Scope references — the one vocabulary for "which part of the station".

The same string names a subject in four places (ADR-0010, AGENTS.md I8):

    frontend URL          #/ops/bay:D03?facet=alarm
    agent tool argument   summary(scope="bay:D03")
    workspace pane key    {kind: 'measurements', scope: 'bay:D03'}
    evidence subject      EvidenceRecord(subject="bay:D03")

Four uses, one concept — which only holds if there is exactly one place that
builds and reads these strings. That place is this module. Nowhere else may
write `f"bay:{bay_id}"`; `tests/unit/test_architecture.py` checks it.

The LLM never invents a scope ref. An operator says "271"; a deterministic
resolver turns that into `device:D03.XCBR1`, or reports that it cannot. Guessing
is forbidden (ADR-0005).
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import model_validator

from blackinterface.domain.models import Frozen, StationGraph
from blackinterface.errors import InvalidInputError

#: Separates kind from id. Consequently an id may never contain it.
SEP = ":"

#: Ids are drawn from OneATS object names: letters, digits, dot, dash,
#: underscore. Deliberately strict — a scope ref ends up in URLs, in tool
#: arguments and in evidence, and a permissive parser here would let junk
#: travel a long way before anyone noticed.
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ScopeKind(StrEnum):
    """What a scope ref points at. Ordered widest first."""

    STATION = "station"
    VOLTAGE_LEVEL = "vl"
    TRANSFORMER = "transformer"
    BUSBAR = "busbar"
    BAY = "bay"
    DEVICE = "device"
    POINT = "point"


#: The station is the only scope with no id — there is exactly one of it.
_NO_ID = (ScopeKind.STATION,)


class ScopeRef(Frozen):
    """A typed pointer at some part of the station.

    Compare and hash by value, so it can key a dict of panes or a cache.
    Render with `str(ref)` or `.ref`; never by string concatenation.
    """

    kind: ScopeKind
    id: str = ""

    @model_validator(mode="after")
    def _check_id(self) -> ScopeRef:
        if self.kind in _NO_ID:
            if self.id:
                raise InvalidInputError(
                    f"scope {self.kind} takes no id", scope=self.kind.value, id=self.id
                )
            return self
        if not self.id:
            raise InvalidInputError(f"scope {self.kind} needs an id", scope=self.kind.value)
        if not _ID.match(self.id):
            raise InvalidInputError(
                f"invalid id for scope {self.kind}: {self.id!r}",
                scope=self.kind.value,
                id=self.id,
            )
        return self

    # ------------------------------------------------------------- rendering
    @property
    def ref(self) -> str:
        """The canonical string. The only way this format is produced."""
        return self.kind.value if self.kind in _NO_ID else f"{self.kind.value}{SEP}{self.id}"

    def __str__(self) -> str:
        return self.ref

    # --------------------------------------------------------------- parsing
    @classmethod
    def parse(cls, text: str) -> ScopeRef:
        """Read a scope ref, or raise InvalidInputError.

        Strict on purpose: an unparseable scope is a bug or a hostile input,
        never a reason to fall back to the whole station. Widening a request
        silently is how a question about one bay gets answered about another.
        """
        raw = (text or "").strip()
        if not raw:
            raise InvalidInputError("empty scope reference")
        kind_text, sep, id_text = raw.partition(SEP)
        try:
            kind = ScopeKind(kind_text)
        except ValueError:
            raise InvalidInputError(
                f"unknown scope kind: {kind_text!r}",
                scope=raw,
                known=[k.value for k in ScopeKind],
            ) from None
        if kind in _NO_ID and sep:
            raise InvalidInputError(f"scope {kind} takes no id", scope=raw)
        return cls(kind=kind, id=id_text.strip())

    # ---------------------------------------------------------- constructors
    @classmethod
    def station(cls) -> ScopeRef:
        return cls(kind=ScopeKind.STATION)

    @classmethod
    def voltage_level(cls, voltage_level: str) -> ScopeRef:
        return cls(kind=ScopeKind.VOLTAGE_LEVEL, id=voltage_level)

    @classmethod
    def transformer(cls, transformer_id: str) -> ScopeRef:
        return cls(kind=ScopeKind.TRANSFORMER, id=transformer_id)

    @classmethod
    def busbar(cls, busbar_id: str) -> ScopeRef:
        return cls(kind=ScopeKind.BUSBAR, id=busbar_id)

    @classmethod
    def bay(cls, bay_id: str) -> ScopeRef:
        return cls(kind=ScopeKind.BAY, id=bay_id)

    @classmethod
    def device(cls, device_id: str) -> ScopeRef:
        return cls(kind=ScopeKind.DEVICE, id=device_id)

    @classmethod
    def point(cls, point_id: str) -> ScopeRef:
        return cls(kind=ScopeKind.POINT, id=point_id)

    # ------------------------------------------------------------- structure
    @property
    def is_station(self) -> bool:
        return self.kind is ScopeKind.STATION

    def parent(self) -> ScopeRef | None:
        """The next scope out, where that is decidable from the id alone.

        `point:D03.XCBR1.PosSt` -> `device:D03.XCBR1` -> `bay:D03` -> `station`.
        A busbar's or a bay's voltage level is *not* derivable from its id —
        that needs the graph, so it is not guessed here. Returns None at the top.
        """
        if self.kind is ScopeKind.STATION:
            return None
        if self.kind is ScopeKind.POINT:
            head, _, _ = self.id.rpartition(".")
            return ScopeRef.device(head) if head else ScopeRef.station()
        if self.kind is ScopeKind.DEVICE:
            head, _, _ = self.id.partition(".")
            return ScopeRef.bay(head) if head else ScopeRef.station()
        return ScopeRef.station()

    def contains(self, other: ScopeRef) -> bool:
        """Whether `other` lies inside this scope, judged from ids alone.

        Only answers what the ids can prove: station contains everything, and
        bay -> device -> point nest by dotted prefix. Voltage level, transformer
        and busbar membership depend on the graph, so `bays_in` answers those
        instead — False here is not "no", it is "not decidable from here".
        """
        if self.kind is ScopeKind.STATION:
            return True
        if self == other:
            return True
        if self.kind is ScopeKind.BAY and other.kind in (ScopeKind.DEVICE, ScopeKind.POINT):
            return other.id.startswith(f"{self.id}.")
        if self.kind is ScopeKind.DEVICE and other.kind is ScopeKind.POINT:
            return other.id.startswith(f"{self.id}.")
        return False


#: What a caller may pass wherever a scope is expected.
ScopeLike = ScopeRef | str


def as_scope(scope: ScopeLike) -> ScopeRef:
    """Accept either form at a boundary, work with `ScopeRef` inside."""
    return scope if isinstance(scope, ScopeRef) else ScopeRef.parse(scope)


def exists(graph: StationGraph, scope: ScopeLike) -> bool:
    """Whether this scope names something the loaded station actually has.

    A point is checked by its `source_ref`-independent id shape only through its
    device: the point catalog lives outside the graph today, so claiming a point
    does not exist would be a stronger statement than we can make (I2).
    """
    ref = as_scope(scope)
    match ref.kind:
        case ScopeKind.STATION:
            return True
        case ScopeKind.VOLTAGE_LEVEL:
            return ref.id in graph.voltage_levels
        case ScopeKind.TRANSFORMER:
            return any(t.id == ref.id for t in graph.transformers)
        case ScopeKind.BUSBAR:
            return any(b.id == ref.id for b in graph.busbars)
        case ScopeKind.BAY:
            return graph.bay(ref.id) is not None
        case ScopeKind.DEVICE:
            return graph.device(ref.id) is not None
        case ScopeKind.POINT:
            parent = ref.parent()
            return parent is not None and exists(graph, parent)


def bays_in(graph: StationGraph, scope: ScopeLike) -> tuple[str, ...]:
    """The bay ids covered by a scope — the workhorse behind every facet.

    This is where voltage-level and busbar membership get answered, because
    both need the graph. A busbar's bays are those with a device terminating on
    its connectivity node: bays that *can* be fed from it, whatever the
    disconnectors happen to be doing right now. Position is a separate question
    and `domain/energization.py` is where it is asked.
    """
    ref = as_scope(scope)
    match ref.kind:
        case ScopeKind.STATION:
            return tuple(b.id for b in graph.bays)
        case ScopeKind.VOLTAGE_LEVEL:
            return tuple(b.id for b in graph.bays if b.voltage_level == ref.id)
        case ScopeKind.TRANSFORMER:
            # The transformer already names its bays, and it names them because
            # each one's display name references it — evidence, not inference.
            transformer = next((t for t in graph.transformers if t.id == ref.id), None)
            if transformer is None:
                return ()
            return tuple(b.id for b in graph.bays if b.id in transformer.bay_ids)
        case ScopeKind.BUSBAR:
            busbar = next((b for b in graph.busbars if b.id == ref.id), None)
            if busbar is None:
                return ()
            attached = {
                d.bay_id
                for d in graph.devices
                if any(t.node_id == busbar.node_id for t in d.terminals)
            }
            return tuple(b.id for b in graph.bays if b.id in attached)
        case ScopeKind.BAY:
            return (ref.id,) if graph.bay(ref.id) is not None else ()
        case ScopeKind.DEVICE | ScopeKind.POINT:
            parent = ref.parent()
            return bays_in(graph, parent) if parent is not None else ()
