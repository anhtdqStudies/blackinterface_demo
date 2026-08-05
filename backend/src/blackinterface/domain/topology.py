"""Build a node-breaker station graph from an observation plus bay templates.

Pure function, no I/O, no OPC UA. Feed it a `StationObs` from either importer
and it produces the same `StationGraph` — which is why the whole thing is
testable from a JSON fixture with the DataServer switched off.

Design rule: when something does not resolve, record a `ValidationIssue` and
keep going with an explicitly marked placeholder. Never guess silently (I7).
"""

from __future__ import annotations

import re

from blackinterface.domain.bay_types import infer_bay_type
from blackinterface.domain.models import (
    Bay,
    BayType,
    Busbar,
    ConnectivityNode,
    Device,
    NodeKind,
    PointSample,
    Severity,
    StationGraph,
    Terminal,
    Transformer,
    ValidationIssue,
)
from blackinterface.domain.observation import BayObs, StationObs
from blackinterface.domain.templates import (
    BUSBAR_REFS,
    EARTH_REF,
    BayTemplate,
    TemplateRegistry,
    default_registry,
)

#: EVN busbar naming: `BB<voltage-code><index>`. Measured on DEMO_SAS v654
#: (2026-08-04): BB11/BB12/BB19 at 110 kV, BB21/BB22/BB29 at 220 kV.
#: ASSUMPTION — not verified: the codes for 22 kV / 35 kV / 500 kV.
VOLTAGE_BUSBAR_CODE: dict[str, str] = {
    "500kV": "5",
    "220kV": "2",
    "110kV": "1",
    "35kV": "3",
    "22kV": "4",
}

EARTH_NODE_ID = "EARTH"

#: LN prefixes that represent switching devices. Anything else in a bay
#: (MMXU, BCU, F21, ...) is measurement or protection and not topology.
SWITCHING_PREFIXES = ("XCBR", "XSWI")


def _busbar_id(voltage_level: str, index: int) -> str | None:
    code = VOLTAGE_BUSBAR_CODE.get(voltage_level)
    return f"BB{code}{index}" if code else None


class _Builder:
    def __init__(self, obs: StationObs, registry: TemplateRegistry) -> None:
        self.obs = obs
        self.registry = registry
        self.nodes: dict[str, ConnectivityNode] = {
            EARTH_NODE_ID: ConnectivityNode(id=EARTH_NODE_ID, kind=NodeKind.EARTH, label="Earth")
        }
        self.busbars: dict[str, Busbar] = {}
        self.devices: list[Device] = []
        self.bays: list[Bay] = []
        self.issues: list[ValidationIssue] = []
        self.observed_busbars = {b.id: b for b in obs.busbars}

    # ---------------------------------------------------------------- busbars
    def resolve_busbar(self, voltage_level: str, ref: str, bay_id: str) -> str:
        """Resolve a template busbar reference to a connectivity node id."""
        if ref == "BB":
            candidates = [b for b in self.busbars.values() if b.voltage_level == voltage_level]
            if len(candidates) == 1:
                return candidates[0].node_id
            index = 1
        else:
            index = int(ref[2:])

        busbar_id = _busbar_id(voltage_level, index)
        if busbar_id is None:
            busbar_id = f"BB?{voltage_level}.{index}"
            self.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="unknown_voltage_code",
                    subject=bay_id,
                    message=(
                        f"No EVN busbar code known for voltage level {voltage_level!r}; "
                        f"invented placeholder busbar {busbar_id}."
                    ),
                )
            )
        return self.ensure_busbar(busbar_id, voltage_level, index, bay_id)

    def ensure_busbar(self, busbar_id: str, voltage_level: str, index: int, bay_id: str) -> str:
        if busbar_id in self.busbars:
            return self.busbars[busbar_id].node_id

        source = self.observed_busbars.get(busbar_id)
        if source is None:
            self.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="busbar_not_in_source",
                    subject=bay_id,
                    message=(
                        f"Bay {bay_id} connects to busbar {busbar_id}, but the DataServer "
                        f"has no such object. Added as inferred; it carries no live data."
                    ),
                )
            )
        node_id = f"NODE.{busbar_id}"
        self.nodes[node_id] = ConnectivityNode(
            id=node_id,
            kind=NodeKind.BUSBAR,
            label=source.name if source else busbar_id,
            voltage_level=voltage_level,
        )
        self.busbars[busbar_id] = Busbar(
            id=busbar_id,
            name=source.name if source else busbar_id,
            voltage_level=voltage_level,
            index=index,
            node_id=node_id,
            is_live=source.is_live if source else PointSample(),
            inferred=source is None,
            source_ref=source.source_ref if source else None,
        )
        return node_id

    # ------------------------------------------------------------------ bays
    def add_bay(self, bay: BayObs) -> None:
        bay_type = infer_bay_type(bay.ln_names)
        template = self.registry.for_bay_type(bay_type)
        issues: list[ValidationIssue] = []

        if bay_type is BayType.UNKNOWN:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code="bay_type_unknown",
                    subject=bay.id,
                    message=(
                        f"No rule matched the logical nodes of {bay.id}: "
                        f"{sorted(bay.ln_names)}. Needs an engineer."
                    ),
                )
            )
        elif template is None:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code="template_missing",
                    subject=bay.id,
                    message=f"Bay type {bay_type} has no template in the registry.",
                )
            )

        device_ids: tuple[str, ...] = ()
        if template is not None:
            device_ids = self.add_devices(bay, template, issues)

        # The `BAY` logical node's Name is the display name an operator knows
        # the bay by ("Ben Cat", "AT1 Incoming"). Measured on DEMO_SAS
        # (2026-08-05): /SAS/220kV/D01/BAY/Name = "AT1 Incoming".
        display = next((ln.name for ln in bay.logical_nodes if ln.ln == "BAY" and ln.name), None)
        self.bays.append(
            Bay(
                id=bay.id,
                name=display or bay.name or bay.id,
                voltage_level=bay.voltage_level,
                bay_type=bay_type,
                template_id=template.id if template else None,
                device_ids=device_ids,
                logical_nodes=tuple(sorted(bay.ln_names)),
                is_live=bay.is_live,
                issues=tuple(issues),
                source_ref=bay.source_ref,
            )
        )

    def add_devices(
        self, bay: BayObs, template: BayTemplate, issues: list[ValidationIssue]
    ) -> tuple[str, ...]:
        observed = {ln.ln: ln for ln in bay.logical_nodes}

        # Internal / external nodes declared by the template, namespaced per bay.
        local: dict[str, str] = {}
        for tnode in template.nodes:
            node_id = f"{bay.id}.{tnode.id}"
            local[tnode.id] = node_id
            self.nodes[node_id] = ConnectivityNode(
                id=node_id,
                kind=tnode.kind,
                label=tnode.label,
                voltage_level=bay.voltage_level,
            )

        def resolve(ref: str) -> str:
            if ref == EARTH_REF:
                return EARTH_NODE_ID
            if ref in BUSBAR_REFS:
                return self.resolve_busbar(bay.voltage_level, ref, bay.id)
            return local[ref]

        device_ids: list[str] = []
        for slot in template.slots:
            found = observed.get(slot.ln)
            if found is None:
                if slot.required:
                    issues.append(
                        ValidationIssue(
                            severity=Severity.ERROR,
                            code="slot_missing",
                            subject=bay.id,
                            message=(
                                f"Template {template.id} requires {slot.ln} "
                                f"({slot.role}) but bay {bay.id} does not have it."
                            ),
                        )
                    )
                continue

            device_id = f"{bay.id}.{slot.ln}"
            terminals = tuple(
                Terminal(device_id=device_id, seq=i, node_id=resolve(ref))
                for i, ref in enumerate(slot.endpoints)
            )
            self.devices.append(
                Device(
                    id=device_id,
                    bay_id=bay.id,
                    ln=slot.ln,
                    role=slot.role,
                    name=found.name or device_id,
                    short_name=found.short_name,
                    position=found.position,
                    terminals=terminals,
                    source_ref=found.source_ref,
                )
            )
            device_ids.append(device_id)

        # Switching devices present in the source but not placed by the template:
        # the topology would be incomplete and we must say so.
        unplaced = sorted(
            ln
            for ln in bay.ln_names
            if ln.startswith(SWITCHING_PREFIXES) and template.slot_for(ln) is None
        )
        if unplaced:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="slot_unmapped",
                    subject=bay.id,
                    message=(
                        f"Bay {bay.id} has switching devices {unplaced} that template "
                        f"{template.id} does not place. They are missing from the graph."
                    ),
                )
            )
        return tuple(device_ids)

    # ----------------------------------------------------------- transformers
    def pair_transformers(self) -> list[Transformer]:
        """Couple bays across voltage levels through their transformer.

        Two evidence sources, both measured on DEMO_SAS — no guessing (I3):

        1. The bay's display name carries the transformer group's id:
           `/SAS/220kV/D01/BAY/Name` = `/SAS/110kV/E07/BAY/Name` = "AT1 Incoming".
        2. The bay's breaker number follows the EVN designation rule
           (Thông tư 44/2014/TT-BCT): a transformer bay's breaker is
           `<voltage digit>3<transformer ordinal>` — AT1 owns 231 (220kV),
           131 (110kV) and 431 (22kV). This is what pairs the tertiary bay
           J01, whose `BAY/Name` is empty.

        A group matched at fewer than two voltage levels stays unpaired and is
        reported — never silently drawn.
        """
        breaker_names: dict[str, list[str]] = {}
        for device in self.devices:
            if device.ln.startswith("XCBR"):
                breaker_names.setdefault(device.bay_id, []).append(device.name)

        result: list[Transformer] = []
        for obs in self.obs.transformers:
            token = re.compile(rf"\b{re.escape(obs.id)}\b", re.IGNORECASE)
            designation = _breaker_designation(obs.id)
            matched = [
                b
                for b in self.bays
                if token.search(b.name)
                or (
                    designation is not None
                    and any(designation.match(name) for name in breaker_names.get(b.id, ()))
                )
            ]
            windings = sorted(matched, key=lambda b: _kilovolts(b.voltage_level), reverse=True)
            if len({b.voltage_level for b in windings}) < 2:
                self.issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code="transformer_unpaired",
                        subject=obs.id,
                        message=(
                            f"The source has transformer {obs.id}, but its id appears in "
                            f"{len(windings)} bay name(s) — need one bay per voltage level "
                            f"to draw the coupling. Not drawn."
                        ),
                    )
                )
                continue
            result.append(
                Transformer(
                    id=obs.id,
                    name=obs.name or obs.id,
                    bay_ids=tuple(b.id for b in windings),
                    source_ref=obs.source_ref,
                )
            )
        return result

    # ----------------------------------------------------------------- build
    def build(self) -> StationGraph:
        for bay in sorted(self.obs.bays, key=lambda b: (b.voltage_level, b.id)):
            self.add_bay(bay)

        # Busbars present in the source but referenced by no bay still belong
        # in the model — they exist electrically.
        for busbar_id, source in self.observed_busbars.items():
            if busbar_id in self.busbars:
                continue
            voltage_level, index = _decode_busbar_id(busbar_id)
            self.ensure_busbar(busbar_id, voltage_level, index, busbar_id)
            self.issues.append(
                ValidationIssue(
                    severity=Severity.INFO,
                    code="busbar_unreferenced",
                    subject=busbar_id,
                    message=(
                        f"Busbar {source.name or busbar_id} exists in the DataServer "
                        f"but no bay in this model connects to it."
                    ),
                )
            )

        transformers = self.pair_transformers()
        voltage_levels = tuple(sorted({b.voltage_level for b in self.bays if b.voltage_level}))
        return StationGraph(
            name=self.obs.name,
            model_version=self.obs.model_version,
            captured_at=self.obs.captured_at,
            source=self.obs.source,
            voltage_levels=voltage_levels,
            busbars=tuple(sorted(self.busbars.values(), key=lambda b: b.id)),
            bays=tuple(self.bays),
            devices=tuple(self.devices),
            nodes=tuple(sorted(self.nodes.values(), key=lambda n: n.id)),
            transformers=tuple(transformers),
            issues=tuple(self.issues),
        )


def _breaker_designation(transformer_id: str) -> re.Pattern[str] | None:
    """EVN breaker number of a transformer bay: `<voltage digit>3<ordinal>`.

    "AT1" -> `^\\d31$`, matching 231/131/431 and nothing else (couplers are
    x12, lines x7x). A transformer id without a single trailing digit gives
    no designation — better unpaired than wrongly paired.
    """
    match = re.search(r"(\d+)$", transformer_id)
    if match is None or len(match.group(1)) != 1:
        return None
    return re.compile(rf"^\d3{match.group(1)}$")


_KV_RE = re.compile(r"([\d.]+)")


def _kilovolts(voltage_level: str) -> float:
    """`"220kV"` -> 220.0. Unparseable levels sort last."""
    match = _KV_RE.search(voltage_level)
    return float(match.group(1)) if match else 0.0


def _decode_busbar_id(busbar_id: str) -> tuple[str, int]:
    """`BB21` -> ("220kV", 1). Falls back to an empty level when unrecognised."""
    digits = busbar_id.removeprefix("BB")
    if len(digits) == 2 and digits.isdigit():
        code, index = digits[0], int(digits[1])
        for level, level_code in VOLTAGE_BUSBAR_CODE.items():
            if level_code == code:
                return level, index
        return "", index
    return "", 0


def build_station(obs: StationObs, registry: TemplateRegistry | None = None) -> StationGraph:
    """Apply bay templates to an observation and return the station graph."""
    return _Builder(obs, registry or default_registry()).build()
