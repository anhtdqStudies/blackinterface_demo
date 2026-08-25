"""Evidence — how an answer knows what it claims to know (ADR-0004, ADR-0013).

Every facet that says something about the station carries one of these. Geometry
and local configuration do not: `/api/diagram` and `/api/projects` make no claim
about a substation.

The record is built by the tool, never written by an LLM (I3). That is not a
style rule — an LLM asked to summarise its own reliability will drop the
inconvenient part, which here is exactly the part that matters.

**Limits are codes, not sentences.** ADR-0013 requires that a degraded answer
say so; it does not require the backend to say so in Vietnamese. The frontend is
translated (ADR-0014) and the agent answers in whatever language it is asked in,
so prose baked in here would end up wrong in both. Same reasoning as the
`reason` codes in `domain/energization.py`.

Nothing here reaches for a clock or a config file: `now` and the staleness
threshold arrive as arguments, so a test can pin them and two runs over the same
data produce the same record.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field

from blackinterface.domain.models import Frozen, PointSample, Quality
from blackinterface.domain.scope import ScopeLike, as_scope

#: A *continuously refreshed* reading older than this is called out, even when
#: its quality is GOOD. GOOD means "the value arrived intact", not "the value is
#: current" — a station that stopped reporting an hour ago has perfectly good
#: stale data.
#:
#: Only points recorded with `expect_refresh=True` are judged this way, and the
#: distinction is not a nicety. An OPC UA `SourceTimestamp` says when the value
#: was *produced*, so a disconnector that has not moved in a day carries a
#: day-old timestamp while being perfectly current. Ageing every point flagged
#: 89 of 159 on a healthy station (measured 2026-08-06) — a caveat that always
#: fires teaches the operator to ignore the evidence block, which is the exact
#: failure this whole envelope exists to prevent.
DEFAULT_STALE_AFTER_MS = 60_000


class SourceKind(StrEnum):
    """Where the numbers in this answer physically came from."""

    OPCUA = "opcua"  # read live from a DataServer subscription or browse
    SNAPSHOT = "snapshot"  # replayed from a stored project snapshot
    FIXTURE = "fixture"  # a dump file — development and tests
    STORE = "store"  # local SQLite (event store, history)
    DERIVED = "derived"  # computed from other facets, no source of its own


class LimitCode(StrEnum):
    """Why an answer is worth less than it looks."""

    POINTS_MISSING = "points_missing"  # asked for points the model has no binding for
    QUALITY_NOT_GOOD = "quality_not_good"  # read them, cannot trust them (I2)
    DATA_STALE = "data_stale"  # trustworthy, but old
    FROM_SNAPSHOT = "from_snapshot"  # structure is remembered, not observed
    LINK_DOWN = "link_down"  # last known values; nobody is listening now
    DEADBAND_APPLIED = "deadband_applied"  # analog values filtered (ADR-0012)
    NO_HISTORY = "no_history"  # the window asked for predates what we store
    UNIT_UNVERIFIED = "unit_unverified"  # the number is real, its scale is not measured


class Limit(Frozen):
    """One caveat, machine-readable so the UI can rank and translate it."""

    code: LimitCode
    count: int = 0
    subjects: tuple[str, ...] = ()  # scope refs or point ids, capped by the builder


class Source(Frozen):
    """The provenance of an answer, down to the release it was pinned to."""

    kind: SourceKind
    endpoint: str | None = None
    node_ids: tuple[str, ...] = ()  # opaque here; only integration/ reads them (I6)
    catalog_snapshot: str | None = None


class Coverage(Frozen):
    """How much of what was asked for could actually be answered.

    `resolved < requested` is the natural home for drift (I7): a NodeId that
    stopped resolving shows up here rather than as a silently shorter list.
    """

    requested: int = 0
    resolved: int = 0
    missing: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.missing and self.resolved >= self.requested


class PointQ(Frozen):
    """One point as it was read, with everything needed to judge it (I2)."""

    point: str
    value: float | int | bool | str | None = None
    quality: Quality = Quality.MISSING
    ts_source: datetime | None = None
    age_ms: int | None = None


class EvidenceRecord(Frozen):
    """What a facet knew, when, from where, and how well.

    `subject` is a scope ref (ADR-0010), so evidence, URL, pane and tool argument
    are the same vocabulary rather than four dialects of it.
    """

    tool: str
    subject: str
    #: Who asked. A username, never "agent" — the agent runs under the
    #: permissions of the person who asked it, so the evidence names that person
    #: (ADR-0016 section 5). `None` only where no caller is known, which today
    #: means a facet computed at startup rather than in response to a request.
    #: Without this field there is no audit trail to reconstruct later.
    actor: str | None = None
    args: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    called_at: datetime
    source: Source
    release: str | None = None
    model_version: str | None = None
    coverage: Coverage = Coverage()
    quality: tuple[PointQ, ...] = ()
    limits: tuple[Limit, ...] = ()

    @property
    def trustworthy(self) -> bool:
        """No caveats at all. Deliberately strict — used by tests, not by UI."""
        return not self.limits


#: Beyond this many, listing every offending point stops informing and starts
#: padding. The count in `Limit.count` stays exact.
_MAX_SUBJECTS = 12


class EvidenceBuilder:
    """Collects points as a facet reads them, then derives the caveats.

    The deriving is the point. ADR-0013 makes `limits` mandatory in five
    situations; leaving that to each facet author means it holds until the first
    hurried one. Here a facet reports *facts* — this point was read, this one is
    missing, this answer came from a snapshot — and the caveats follow.

    A facet may still add a caveat by hand (`note`), never remove one.
    """

    def __init__(
        self,
        tool: str,
        subject: ScopeLike,
        *,
        source: Source,
        actor: str | None = None,
        args: dict[str, str | int | float | bool | None] | None = None,
        release: str | None = None,
        model_version: str | None = None,
        stale_after_ms: int = DEFAULT_STALE_AFTER_MS,
    ) -> None:
        self._tool = tool
        self._subject = as_scope(subject)
        self._source = source
        self._actor = actor
        self._args = dict(args or {})
        self._release = release
        self._model_version = model_version
        self._stale_after_ms = stale_after_ms
        self._points: list[PointQ] = []
        self._ageing: set[str] = set()
        self._missing: list[str] = []
        self._notes: list[Limit] = []

    # ------------------------------------------------------------- gathering
    def point(
        self,
        point_id: str,
        sample: PointSample,
        *,
        expect_refresh: bool = False,
        now: datetime | None = None,
    ) -> PointQ:
        """Record one reading. Returns it, so a caller can use it in the payload.

        `expect_refresh` says this point is *supposed* to keep arriving — an
        analog measurement, not a switch position. Only those are judged stale;
        see `DEFAULT_STALE_AFTER_MS` for why ageing the rest is actively
        harmful. `age_ms` is still reported for every point, because how old a
        value is remains worth showing even when it is not a fault.
        """
        moment = now or datetime.now(UTC)
        age: int | None = None
        if sample.source_timestamp is not None:
            stamped = sample.source_timestamp
            if stamped.tzinfo is None:  # OneATS timestamps arrive naive UTC
                stamped = stamped.replace(tzinfo=UTC)
            age = max(0, int((moment - stamped).total_seconds() * 1000))
        read = PointQ(
            point=point_id,
            value=sample.value,
            quality=sample.quality,
            ts_source=sample.source_timestamp,
            age_ms=age,
        )
        self._points.append(read)
        if expect_refresh:
            self._ageing.add(point_id)
        return read

    def points(
        self,
        samples: Iterable[tuple[str, PointSample]],
        *,
        expect_refresh: bool = False,
        now: datetime | None = None,
    ) -> None:
        moment = now or datetime.now(UTC)
        for point_id, sample in samples:
            self.point(point_id, sample, expect_refresh=expect_refresh, now=moment)

    def missing(self, *point_ids: str) -> None:
        """Points that were asked for and have no binding at all (I7 drift)."""
        self._missing.extend(point_ids)

    def note(self, code: LimitCode, *, count: int = 0, subjects: Iterable[str] = ()) -> None:
        """Add a caveat the facet knows about and the readings cannot show —
        a stale snapshot, a dropped link, a deadband that filtered the values."""
        listed = tuple(subjects)
        self._notes.append(
            Limit(code=code, count=count or len(listed), subjects=listed[:_MAX_SUBJECTS])
        )

    # -------------------------------------------------------------- building
    def build(self, *, now: datetime | None = None) -> EvidenceRecord:
        called_at = now or datetime.now(UTC)
        coverage = Coverage(
            requested=len(self._points) + len(self._missing),
            resolved=len(self._points),
            missing=tuple(self._missing),
        )
        return EvidenceRecord(
            tool=self._tool,
            subject=self._subject.ref,
            actor=self._actor,
            args=self._args,
            called_at=called_at,
            source=self._source,
            release=self._release,
            model_version=self._model_version,
            coverage=coverage,
            quality=tuple(self._points),
            limits=self._derive_limits(coverage),
        )

    def _derive_limits(self, coverage: Coverage) -> tuple[Limit, ...]:
        limits: list[Limit] = []
        if coverage.missing:
            limits.append(
                Limit(
                    code=LimitCode.POINTS_MISSING,
                    count=len(coverage.missing),
                    subjects=coverage.missing[:_MAX_SUBJECTS],
                )
            )
        bad = [p.point for p in self._points if p.quality is not Quality.GOOD]
        if bad:
            limits.append(
                Limit(
                    code=LimitCode.QUALITY_NOT_GOOD,
                    count=len(bad),
                    subjects=tuple(bad[:_MAX_SUBJECTS]),
                )
            )
        stale = [
            p.point
            for p in self._points
            if p.point in self._ageing and p.age_ms is not None and p.age_ms > self._stale_after_ms
        ]
        if stale:
            limits.append(
                Limit(
                    code=LimitCode.DATA_STALE,
                    count=len(stale),
                    subjects=tuple(stale[:_MAX_SUBJECTS]),
                )
            )
        if self._source.kind is SourceKind.SNAPSHOT:
            limits.append(Limit(code=LimitCode.FROM_SNAPSHOT, count=1))
        return tuple(limits) + tuple(self._notes)
