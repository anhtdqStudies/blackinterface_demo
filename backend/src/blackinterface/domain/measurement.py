"""Analog values, and the rules that keep them from lying.

A measurement is a *label on* the station, never a statement *about its
topology* (ADR-0012, rule 1). Nothing here touches `StationGraph`, and nothing
here can change which conductor is energised. That separation is the whole
point: a storm of power readings must not delay the handling of a breaker that
just tripped.

Three decisions live in this module, and each is a safety decision.

**1. A unit is never guessed.** The DataServer publishes no `EngineeringUnits`
property on any measurand (browsed 2026-08-06 on DEMO_SAS v654: `MMXU1`,
`YLTC`, `Subs/BB21` all expose bare `Float`/`Int32` variables). So the
*dimension* is known from IEC 61850 — `Vlin` is a voltage — but the *scale* is
not: 221.08 could be volts on a 221 V busbar or kilovolts on a 220 kV one.
Writing "221.08 V" beside a 220 kV busbar would be worse than writing nothing.
Therefore every measurand whose prefix could be wrong carries `Unit.UNKNOWN`,
the UI shows the quantity's name instead of a unit, and the evidence envelope
records `LimitCode.UNIT_UNVERIFIED`. `Hz`, power factor and tap position are
exempt: those three cannot be mis-scaled. Open question Q7 in
`docs/90-progress/status.md` — ask ATS for the scaling, then delete this
paragraph, not before.

**2. A deadband is per quantity, not per installation.** One global percentage
cannot serve both power and frequency: 0.5 % of 50 Hz is 0.25 Hz, an enormous
excursion, while 0.5 % of a load is noise. Each measurand therefore declares
its own threshold, and `BI_MEASUREMENT_DEADBAND_PCT` only *overrides* them when
an installation knows better.

**3. Tap position has no deadband at all.** It is discrete, like a switch
position. Smoothing it would hide a tap operation, which is exactly the event
an operator is watching for.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from blackinterface.domain.models import Frozen, PointSample, Quality
from blackinterface.domain.observation import BayObs, StationObs, TransformerObs
from blackinterface.domain.scope import ScopeLike, ScopeRef, as_scope


class Quantity(StrEnum):
    """What is being measured. Always known; unlike the unit, never in doubt."""

    ACTIVE_POWER = "active_power"
    REACTIVE_POWER = "reactive_power"
    POWER_FACTOR = "power_factor"
    VOLTAGE = "voltage"
    CURRENT = "current"
    FREQUENCY = "frequency"
    TAP_POSITION = "tap_position"


class Unit(StrEnum):
    """The unit to print after the number, when we are entitled to print one.

    `UNKNOWN` is a deliberate sentinel rather than an empty string: it must be
    impossible to confuse "we did not measure the scale" with "this quantity is
    dimensionless". Power factor is the second case and gets `NONE`.
    """

    UNKNOWN = "?"
    NONE = ""
    HERTZ = "Hz"
    STEP = "step"


class Measurand(Frozen):
    """One analog point in the catalog: where to find it and how to judge it."""

    #: Logical node it hangs under, or "" when the owner carries it directly
    #: (a busbar's `Hz` sits on `/SAS/Subs/BB21` itself).
    ln: str = ""
    #: Data attribute name, exactly as OneATS spells it. Case matters: the
    #: busbar voltage is `PPVmax`, not `PPVMax`.
    da: str
    quantity: Quantity
    unit: Unit = Unit.UNKNOWN
    #: Relative threshold, percent of the previous reading.
    deadband_pct: float = 0.0
    #: Absolute floor, so a value hovering near zero does not chatter.
    deadband_abs: float = 0.0

    @property
    def key(self) -> str:
        """Stable identifier within its owner, e.g. `MMXU1.totW` or `Hz`."""
        return f"{self.ln}.{self.da}" if self.ln else self.da


#: Per-bay measurands. `MMXU1` is present on every bay that has instrument
#: transformers; bays without it simply produce no readings (measured
#: 2026-08-06: 11 of 12 bays on DEMO_SAS carry one).
BAY_MEASURANDS: tuple[Measurand, ...] = (
    Measurand(ln="MMXU1", da="totW", quantity=Quantity.ACTIVE_POWER, deadband_pct=0.5),
    Measurand(ln="MMXU1", da="totVAr", quantity=Quantity.REACTIVE_POWER, deadband_pct=0.5),
    Measurand(ln="MMXU1", da="Vlin", quantity=Quantity.VOLTAGE, deadband_pct=0.2),
    Measurand(ln="MMXU1", da="Amax", quantity=Quantity.CURRENT, deadband_pct=0.5),
    Measurand(
        ln="MMXU1",
        da="Hz",
        quantity=Quantity.FREQUENCY,
        unit=Unit.HERTZ,
        deadband_abs=0.01,
    ),
    Measurand(
        ln="MMXU1",
        da="totPF",
        quantity=Quantity.POWER_FACTOR,
        unit=Unit.NONE,
        deadband_abs=0.005,
    ),
)

#: Busbar measurands. These sit directly on `/SAS/Subs/<BB>`, no logical node.
BUSBAR_MEASURANDS: tuple[Measurand, ...] = (
    Measurand(da="PPVmax", quantity=Quantity.VOLTAGE, deadband_pct=0.2),
    Measurand(da="Hz", quantity=Quantity.FREQUENCY, unit=Unit.HERTZ, deadband_abs=0.01),
)

#: Transformer measurands. No deadband — see decision 3 in the module docstring.
TRANSFORMER_MEASURANDS: tuple[Measurand, ...] = (
    Measurand(ln="YLTC", da="TapPos", quantity=Quantity.TAP_POSITION, unit=Unit.STEP),
)

ALL_MEASURANDS: tuple[Measurand, ...] = BAY_MEASURANDS + BUSBAR_MEASURANDS + TRANSFORMER_MEASURANDS


def wanted_das(measurands: tuple[Measurand, ...], ln: str = "") -> frozenset[str]:
    """Data attribute names an importer should read under `ln`.

    Importers ask the catalog rather than keeping their own list, so adding a
    measurand here is enough to make both the live browser and the dump reader
    pick it up.
    """
    return frozenset(m.da for m in measurands if m.ln == ln)


#: Logical nodes an importer must descend into for measurements. Switching LNs
#: are found by their own rule; these are the extra ones.
MEASURAND_LNS: frozenset[str] = frozenset(m.ln for m in ALL_MEASURANDS if m.ln)


class Reading(Frozen):
    """One measurand, attached to the thing it is about."""

    subject: ScopeRef
    measurand: Measurand
    sample: PointSample

    @property
    def id(self) -> str:
        """Unique across the station: `bay:D03/MMXU1.totW`."""
        return f"{self.subject.ref}/{self.measurand.key}"

    @property
    def point(self) -> ScopeRef:
        """The same reading addressed as a point, e.g. `point:D03.MMXU1.totW`.

        Evidence names its points in the scope vocabulary like everything else
        (ADR-0010), so a caveat about one number can be joined back to the
        panel showing it without a second naming scheme in between.
        """
        return ScopeRef.point(f"{self.subject.id}.{self.measurand.key}")

    @property
    def number(self) -> float | None:
        """The value as a number, or None when it is not one.

        Quality gates this the same way `Device.state` gates a position (I2):
        a reading whose quality is not GOOD has no number, it has a gap.
        """
        if self.sample.quality is not Quality.GOOD:
            return None
        raw = self.sample.value
        if isinstance(raw, bool) or not isinstance(raw, int | float):
            return None
        return float(raw)


class MeasurementSet(Frozen):
    """Every reading the current observation holds, in catalog order.

    Rebuilt whole on each measurement batch. That is the same trade the graph
    makes — a hundred readings cost microseconds, and rebuilding guarantees the
    set matches the observation rather than drifting from it.
    """

    readings: tuple[Reading, ...] = ()

    def of(self, scope: ScopeLike) -> tuple[Reading, ...]:
        """Readings whose subject is exactly this scope."""
        ref = as_scope(scope)
        return tuple(r for r in self.readings if r.subject == ref)

    def subjects(self) -> tuple[ScopeRef, ...]:
        """Distinct subjects, first-seen order."""
        seen: dict[ScopeRef, None] = {}
        for reading in self.readings:
            seen.setdefault(reading.subject, None)
        return tuple(seen)

    @property
    def point_refs(self) -> tuple[str, ...]:
        """Source refs behind these readings — what evidence counts as coverage."""
        return tuple(r.sample.source_ref for r in self.readings if r.sample.source_ref)


def read_measurements(obs: StationObs) -> MeasurementSet:
    """Interpret an observation's raw measurands through the catalog. Pure."""
    readings: list[Reading] = []
    for bay in obs.bays:
        readings.extend(_readings_for(ScopeRef.bay(bay.id), _measurands_of(bay), BAY_MEASURANDS))
    for busbar in obs.busbars:
        readings.extend(
            _readings_for(
                ScopeRef.busbar(busbar.id),
                {m.da: m.sample for m in busbar.measurands},
                BUSBAR_MEASURANDS,
            )
        )
    for transformer in obs.transformers:
        readings.extend(
            _readings_for(
                ScopeRef.transformer(transformer.id),
                _measurands_of(transformer),
                TRANSFORMER_MEASURANDS,
            )
        )
    return MeasurementSet(readings=tuple(readings))


def _measurands_of(owner: BayObs | TransformerObs) -> dict[str, PointSample]:
    """Flatten an owner's logical nodes into `<LN>.<DA>` -> sample."""
    return {f"{ln.ln}.{m.da}": m.sample for ln in owner.logical_nodes for m in ln.measurands}


def _readings_for(
    subject: ScopeRef,
    samples: Mapping[str, PointSample],
    catalog: tuple[Measurand, ...],
) -> list[Reading]:
    """One subject's readings. A measurand the source did not carry is left out
    rather than reported as an empty value — absent and unreadable are different
    facts, and `Coverage.missing` is where the first one belongs."""
    return [
        Reading(subject=subject, measurand=measurand, sample=samples[measurand.key])
        for measurand in catalog
        if measurand.key in samples
    ]


# ------------------------------------------------------------------- deadband


def significant(
    previous: PointSample,
    fresh: PointSample,
    measurand: Measurand,
    *,
    pct_override: float | None = None,
) -> bool:
    """Whether this new reading is worth telling anyone about.

    Quality is never deadbanded: a point going BAD, or coming back GOOD, is
    news whatever the number does. Only a GOOD-to-GOOD numeric move can be
    judged small enough to drop.
    """
    if previous.quality is not fresh.quality:
        return True
    if fresh.quality is not Quality.GOOD:
        return False  # still bad, still the same kind of bad
    old, new = _number(previous), _number(fresh)
    if old is None or new is None:
        return old is not new  # one of them is unusable: that is a change
    threshold = max(
        measurand.deadband_abs,
        abs(old) * (measurand.deadband_pct if pct_override is None else pct_override) / 100.0,
    )
    return abs(new - old) > threshold


def filter_deadband(
    obs: StationObs,
    samples: Mapping[str, PointSample],
    *,
    pct_override: float | None = None,
) -> dict[str, PointSample]:
    """Drop the readings that moved too little to matter. Pure.

    Anything not recognised as a catalogued measurand passes through untouched:
    this function's job is to quieten known analog points, not to be a gate on
    the batch. A ref it does not know is one the caller routed here by mistake,
    and swallowing it would hide that.
    """
    known = _by_source_ref(obs)
    kept: dict[str, PointSample] = {}
    for ref, fresh in samples.items():
        found = known.get(ref)
        if found is None:
            kept[ref] = fresh
            continue
        measurand, previous = found
        if significant(previous, fresh, measurand, pct_override=pct_override):
            kept[ref] = fresh
    return kept


def _by_source_ref(obs: StationObs) -> dict[str, tuple[Measurand, PointSample]]:
    """Address -> (what it measures, what it last read)."""
    index: dict[str, tuple[Measurand, PointSample]] = {}
    catalogs: tuple[tuple[dict[str, PointSample], tuple[Measurand, ...]], ...] = (
        *((_measurands_of(bay), BAY_MEASURANDS) for bay in obs.bays),
        *(
            ({m.da: m.sample for m in busbar.measurands}, BUSBAR_MEASURANDS)
            for busbar in obs.busbars
        ),
        *((_measurands_of(t), TRANSFORMER_MEASURANDS) for t in obs.transformers),
    )
    for samples, catalog in catalogs:
        for measurand in catalog:
            sample = samples.get(measurand.key)
            if sample is not None and sample.source_ref:
                index[sample.source_ref] = (measurand, sample)
    return index


def _number(sample: PointSample) -> float | None:
    raw = sample.value
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        return None
    return float(raw)
