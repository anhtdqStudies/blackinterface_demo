"""Which conductors are live — solved from topology, seeded from measurement.

WHAT THIS ANSWERS: "is this section energised *from inside this station*, with
the switch positions we can currently read?" That is the question a single-line
diagram colours, and the same question OneATS's own `CheckLiveState` Lua answers
(see the formulas quoted in the bay templates).

WHAT IT DOES NOT ANSWER: whether a section is safe to work on. A line
disconnected at our end is normally still energised from the remote end, and
this solver has no data about the far end. `EARTHED` is the only state here that
carries a safety meaning, and even it means "a closed earth switch is bonded to
this section", not "cleared for work".

HOW IT WORKS

1.  Closed switching devices bond their two nodes together. Do that for every
    device and the station falls into *islands*: sets of nodes that are one
    conductor as things stand. This is the only place topology enters, and it
    uses positions exactly as measured — `UNDETERMINED` never bonds.
2.  Islands are seeded from the busbars, because that is what the station
    actually measures: `Subs.BB*.IsLive`. Bay-level `IsLive` is deliberately NOT
    used as a seed — OneATS derives it from the busbars, so consuming it would
    make our result a restatement of theirs instead of an independent check.
3.  The verdict spreads outward: definitely through a power transformer (both
    windings of an energised transformer are energised), and — as *uncertainty*
    only — across devices whose position we cannot read.
4.  Whatever is left has no source reachable through any closed or unreadable
    device. That is `DEAD`, unless the island holds a busbar whose own `IsLive`
    is unusable, in which case we know nothing and say `UNKNOWN`.

The safety rule that shapes every branch (AGENTS.md I2): **we never infer
"dead"**. Missing data, unreadable positions and contradictions all resolve to
`UNKNOWN`, never to the one word that makes someone reach into a cubicle.

Finally the result is cross-checked against the bay-level `IsLive` OneATS
publishes. A disagreement means one of the two models is wrong — most likely a
bay template of ours — and is reported, never smoothed over (I7).
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from blackinterface.domain.models import (
    DeviceRole,
    Frozen,
    NodeKind,
    Quality,
    Severity,
    StationGraph,
    SwitchState,
    ValidationIssue,
)


class LiveState(StrEnum):
    """Energisation verdict for one island.

    `UNKNOWN` is a first-class answer, not a failure: it is what an honest
    system says when the data cannot support `LIVE` or `DEAD`.
    """

    LIVE = "LIVE"
    DEAD = "DEAD"
    EARTHED = "EARTHED"
    UNKNOWN = "UNKNOWN"


class Reason(StrEnum):
    """Why an island got its state.

    A code, not a sentence. Operators read Vietnamese and the wording belongs to
    the UI; the API must not freeze it.
    """

    SEEDED_LIVE = "seeded_live"  # a busbar here measures live
    SEEDED_DEAD = "seeded_dead"  # a busbar here measures dead
    THROUGH_TRANSFORMER = "through_transformer"  # the other winding is energised
    POSSIBLE_VIA_UNCERTAIN = "possible_via_uncertain"  # an unreadable device may bond it
    EARTHED = "earthed"  # a closed earth switch is bonded here
    NO_MEASUREMENT = "no_measurement"  # its busbar's IsLive is unusable
    ISOLATED = "isolated"  # every path to a source is definitely open


class Island(Frozen):
    """A set of nodes that are one conductor, with one verdict for all of them."""

    id: str  # "ISL.<lowest node id>" — stable across runs
    state: LiveState
    reason: Reason
    voltage_level: str = ""
    node_ids: tuple[str, ...] = ()
    busbar_ids: tuple[str, ...] = ()
    bay_ids: tuple[str, ...] = ()
    seeds: tuple[str, ...] = ()  # busbars whose measurement decided this
    earthed_by: tuple[str, ...] = ()  # closed earth switches bonded here
    via: str = ""  # transformer/device that carried the verdict in


class NodeLive(Frozen):
    node_id: str
    island_id: str
    state: LiveState


class CrossCheck(Frozen):
    """Our verdict for a bay against the one OneATS publishes for it.

    `agrees is None` means the comparison could not be made — either we say
    `UNKNOWN` or OneATS's `IsLive` is not readable. Not comparable is not the
    same as agreeing, and is never counted as one.
    """

    bay_id: str
    node_id: str
    computed: LiveState
    reported: bool | None = None
    quality: Quality = Quality.MISSING
    agrees: bool | None = None


class EnergizationResult(Frozen):
    islands: tuple[Island, ...] = ()
    nodes: tuple[NodeLive, ...] = ()
    checks: tuple[CrossCheck, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()

    def state_of(self, node_id: str) -> LiveState:
        """Verdict for one node; `UNKNOWN` when the node is not in the graph."""
        return next(
            (n.state for n in self.nodes if n.node_id == node_id),
            LiveState.UNKNOWN,
        )

    @property
    def mismatches(self) -> tuple[CrossCheck, ...]:
        return tuple(c for c in self.checks if c.agrees is False)


class _Solver:
    def __init__(self, graph: StationGraph) -> None:
        self.graph = graph
        self.kind = {n.id: n.kind for n in graph.nodes}
        self.level = {n.id: n.voltage_level for n in graph.nodes}
        # Earth is left out of the partition on purpose. Two earthed sections
        # are joined through the earth grid, but they are not one conductor in
        # any sense that matters here; merging them would let a verdict jump
        # between unrelated bays.
        self.earth = {n.id for n in graph.nodes if n.kind is NodeKind.EARTH}
        self.parent = {n.id: n.id for n in graph.nodes if n.id not in self.earth}

        self.uncertain: list[tuple[str, str, str]] = []  # device id, node, node
        self.earthed_by: dict[str, list[str]] = defaultdict(list)
        self.issues: list[ValidationIssue] = []

    # ------------------------------------------------------------ union-find
    def find(self, node_id: str) -> str:
        root = node_id
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[node_id] != root:  # path compression
            self.parent[node_id], node_id = root, self.parent[node_id]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # Lowest id wins, so island ids do not depend on device order (I4).
        low, high = sorted((ra, rb))
        self.parent[high] = low

    # ---------------------------------------------------------------- step 1
    def bond(self) -> None:
        """Merge nodes joined by a closed device; note the rest for later."""
        for device in self.graph.devices:
            ends = [t.node_id for t in device.terminals]
            if device.role is DeviceRole.EARTH_SWITCH:
                if device.state is SwitchState.CLOSED:
                    for node in ends:
                        if node in self.parent:
                            self.earthed_by[node].append(device.id)
                continue
            live_ends = [n for n in ends if n in self.parent]
            if len(live_ends) < 2:
                continue
            if device.state is SwitchState.CLOSED:
                self.union(live_ends[0], live_ends[1])
            elif device.state is not SwitchState.OPEN:
                # INTERMEDIATE or UNDETERMINED: it may or may not be bonding
                # these two nodes right now, and pretending otherwise is how a
                # diagram tells someone a live section is dead.
                self.uncertain.append((device.id, live_ends[0], live_ends[1]))

    # ---------------------------------------------------------------- step 2
    def members(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for node_id in sorted(self.parent):
            grouped[self.find(node_id)].append(node_id)
        return grouped

    def winding_node(self, bay_id: str) -> str | None:
        """Where the power transformer attaches to this bay.

        Read off the template's own wiring instead of guessed: the bay's
        transformer disconnector has one end on the bay spine and one end on
        the transformer. In an HV incomer bay that far end is the external
        winding node (T2: `-3` between `n_mid` and `n_tr`); in the 22 kV
        switchgear it is the incomer the template still models as a busbar
        (T5: `-3` between `BB` and `n_a`), which electrically *is* the LV
        winding. One rule covers both: the end that is not an internal node.
        """
        for device in self.graph.devices_of(bay_id):
            if device.role is not DeviceRole.TRANSFORMER_DISCONNECTOR:
                continue
            far = [
                t.node_id
                for t in device.terminals
                if self.kind.get(t.node_id) is not NodeKind.INTERNAL and t.node_id in self.parent
            ]
            if far:
                return far[0]
        # No disconnector modelled: fall back to where the bay leaves.
        external = [
            t.node_id
            for d in self.graph.devices_of(bay_id)
            for t in d.terminals
            if self.kind.get(t.node_id) is NodeKind.EXTERNAL
        ]
        return external[0] if external else None

    def bay_external_node(self, bay_id: str) -> str | None:
        for device in self.graph.devices_of(bay_id):
            for terminal in device.terminals:
                if self.kind.get(terminal.node_id) is NodeKind.EXTERNAL:
                    return terminal.node_id
        return None

    # ---------------------------------------------------------------- step 3
    def solve(self) -> EnergizationResult:
        self.bond()
        grouped = self.members()

        live_seeds: dict[str, list[str]] = defaultdict(list)
        dead_seeds: dict[str, list[str]] = defaultdict(list)
        blind_busbars: dict[str, list[str]] = defaultdict(list)
        busbars_of: dict[str, list[str]] = defaultdict(list)
        for busbar in self.graph.busbars:
            if busbar.node_id not in self.parent:
                continue
            root = self.find(busbar.node_id)
            busbars_of[root].append(busbar.id)
            sample = busbar.is_live
            if sample.usable and isinstance(sample.value, bool):
                (live_seeds if sample.value else dead_seeds)[root].append(busbar.id)
            else:
                # The station has a measurement point here and it is not
                # readable. Silence from a point that should speak is not
                # evidence of anything (I2).
                blind_busbars[root].append(busbar.id)

        earthed_roots: dict[str, list[str]] = defaultdict(list)
        for node_id, devices in self.earthed_by.items():
            earthed_roots[self.find(node_id)].extend(devices)

        state: dict[str, LiveState | None] = {}
        reason: dict[str, Reason] = {}
        via: dict[str, str] = {}
        for root in grouped:
            if live_seeds[root]:
                state[root], reason[root] = LiveState.LIVE, Reason.SEEDED_LIVE
                self._report_conflicts(root, live_seeds, dead_seeds, earthed_roots)
            elif earthed_roots[root]:
                state[root], reason[root] = LiveState.EARTHED, Reason.EARTHED
            elif dead_seeds[root]:
                state[root], reason[root] = LiveState.DEAD, Reason.SEEDED_DEAD
            else:
                state[root] = None  # undecided; steps 4 and 5 will settle it

        self._spread(state, reason, via)

        for root, verdict in state.items():
            if verdict is not None:
                continue
            if blind_busbars[root]:
                state[root], reason[root] = LiveState.UNKNOWN, Reason.NO_MEASUREMENT
            else:
                state[root], reason[root] = LiveState.DEAD, Reason.ISOLATED

        return self._assemble(
            grouped,
            state,
            reason,
            via,
            live_seeds,
            dead_seeds,
            blind_busbars,
            busbars_of,
            earthed_roots,
        )

    # ---------------------------------------------------------------- step 4
    def _spread(
        self,
        state: dict[str, LiveState | None],
        reason: dict[str, Reason],
        via: dict[str, str],
    ) -> None:
        """Carry verdicts outward until nothing changes.

        Two very different mechanisms, deliberately kept apart:

        * a transformer carries the *same* verdict to its other windings, because
          energising one winding energises the rest — there is no switch inside;
        * an unreadable device carries only *doubt*: a section it might be
          bonding to something live becomes `UNKNOWN`, never `LIVE` (we do not
          know) and never `DEAD` (that is the dangerous direction).
        """
        windings = [
            (transformer.id, [self.winding_node(b) for b in transformer.bay_ids])
            for transformer in self.graph.transformers
        ]
        for transformer_id, nodes in windings:
            if any(n is None for n in nodes):
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="transformer_winding_unresolved",
                        subject=transformer_id,
                        message=(
                            f"Transformer {transformer_id} is paired, but one winding's "
                            f"attachment node could not be found in the graph. That "
                            f"winding is left out of the energisation spread."
                        ),
                    )
                )

        changed = True
        while changed:
            changed = False
            for transformer_id, nodes in windings:
                roots = [self.find(n) for n in nodes if n is not None]
                verdicts = {state[r] for r in roots}
                carried = (
                    LiveState.LIVE
                    if LiveState.LIVE in verdicts
                    else (LiveState.UNKNOWN if LiveState.UNKNOWN in verdicts else None)
                )
                if carried is None:
                    continue
                for root in roots:
                    if state[root] is None:
                        state[root], reason[root] = carried, Reason.THROUGH_TRANSFORMER
                        via[root] = transformer_id
                        changed = True
                    elif state[root] is LiveState.EARTHED and carried is LiveState.LIVE:
                        self._earthed_while_live(root, transformer_id)

            for device_id, a, b in self.uncertain:
                for source, target in ((a, b), (b, a)):
                    root_source, root_target = self.find(source), self.find(target)
                    if state[root_target] is not None:
                        continue
                    if state[root_source] in (LiveState.LIVE, LiveState.UNKNOWN):
                        state[root_target] = LiveState.UNKNOWN
                        reason[root_target] = Reason.POSSIBLE_VIA_UNCERTAIN
                        via[root_target] = device_id
                        changed = True

    def _report_conflicts(
        self,
        root: str,
        live_seeds: dict[str, list[str]],
        dead_seeds: dict[str, list[str]],
        earthed_roots: dict[str, list[str]],
    ) -> None:
        if dead_seeds[root]:
            self.issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code="energization_conflict",
                    subject=live_seeds[root][0],
                    message=(
                        f"Busbars {live_seeds[root]} and {dead_seeds[root]} are bonded "
                        f"into one conductor by closed devices, yet report opposite "
                        f"IsLive. Either a switch position or a bay template is wrong. "
                        f"Reported live, the safe reading."
                    ),
                )
            )
        if earthed_roots[root]:
            self.issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code="earthed_while_live",
                    subject=earthed_roots[root][0],
                    message=(
                        f"Earth switches {earthed_roots[root]} are closed on a section "
                        f"that measures live ({live_seeds[root]}). That is a fault "
                        f"condition or bad data — check before trusting either."
                    ),
                )
            )

    def _earthed_while_live(self, root: str, transformer_id: str) -> None:
        self.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="earthed_while_live",
                subject=transformer_id,
                message=(
                    f"A section earthed by a closed earth switch is fed through "
                    f"transformer {transformer_id} from an energised winding. That is a "
                    f"fault condition or bad data — check before trusting either."
                ),
            )
        )

    # ---------------------------------------------------------------- step 5
    def _assemble(
        self,
        grouped: dict[str, list[str]],
        state: dict[str, LiveState | None],
        reason: dict[str, Reason],
        via: dict[str, str],
        live_seeds: dict[str, list[str]],
        dead_seeds: dict[str, list[str]],
        blind_busbars: dict[str, list[str]],
        busbars_of: dict[str, list[str]],
        earthed_roots: dict[str, list[str]],
    ) -> EnergizationResult:
        bays_of: dict[str, set[str]] = defaultdict(set)
        for device in self.graph.devices:
            for terminal in device.terminals:
                if terminal.node_id in self.parent:
                    bays_of[self.find(terminal.node_id)].add(device.bay_id)

        islands: list[Island] = []
        nodes: list[NodeLive] = []
        for root in sorted(grouped):
            verdict = state[root] or LiveState.UNKNOWN
            island_id = f"ISL.{root}"
            levels = [self.level.get(n, "") for n in grouped[root]]
            islands.append(
                Island(
                    id=island_id,
                    state=verdict,
                    reason=reason[root],
                    voltage_level=next((v for v in levels if v), ""),
                    node_ids=tuple(grouped[root]),
                    busbar_ids=tuple(sorted(busbars_of[root])),
                    bay_ids=tuple(sorted(bays_of[root])),
                    seeds=tuple(live_seeds[root] or dead_seeds[root] or blind_busbars[root]),
                    earthed_by=tuple(sorted(earthed_roots[root])),
                    via=via.get(root, ""),
                )
            )
            nodes.extend(
                NodeLive(node_id=node_id, island_id=island_id, state=verdict)
                for node_id in grouped[root]
            )

        return EnergizationResult(
            islands=tuple(islands),
            nodes=tuple(nodes),
            checks=self._cross_check(state),
            issues=tuple(self.issues),
        )

    # ---------------------------------------------------------------- step 6
    def _cross_check(self, state: dict[str, LiveState | None]) -> tuple[CrossCheck, ...]:
        """Compare our verdict with the bay-level `IsLive` OneATS publishes.

        This is the point of seeding from busbars only: OneATS derives bay
        `IsLive` from the same busbars through its own `CheckLiveState` logic,
        so agreement here means two independent paths reached the same answer,
        and disagreement means one of the two models is wrong. Ours usually —
        it is the young one.
        """
        checks: list[CrossCheck] = []
        for bay in self.graph.bays:
            node_id = self.bay_external_node(bay.id)
            if node_id is None or node_id not in self.parent:
                continue
            computed = state[self.find(node_id)] or LiveState.UNKNOWN
            sample = bay.is_live
            reported = sample.value if sample.usable and isinstance(sample.value, bool) else None
            agrees: bool | None = None
            if reported is not None and computed is not LiveState.UNKNOWN:
                agrees = (computed is LiveState.LIVE) == reported
            checks.append(
                CrossCheck(
                    bay_id=bay.id,
                    node_id=node_id,
                    computed=computed,
                    reported=reported,
                    quality=sample.quality,
                    agrees=agrees,
                )
            )
            if agrees is False:
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="energization_mismatch",
                        subject=bay.id,
                        message=(
                            f"Bay {bay.id}: we compute {computed} from the switch "
                            f"positions, OneATS reports IsLive={reported}. One of the "
                            f"two is wrong — most likely this bay's template."
                        ),
                    )
                )
        return tuple(checks)


def solve_energization(graph: StationGraph) -> EnergizationResult:
    """Partition the station into live/dead sections. Pure, deterministic (I4)."""
    return _Solver(graph).solve()


__all__ = [
    "CrossCheck",
    "EnergizationResult",
    "Island",
    "LiveState",
    "NodeLive",
    "Reason",
    "solve_energization",
]
