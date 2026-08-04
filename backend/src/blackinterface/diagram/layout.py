"""Turn a station graph into coordinates. Deterministic, no LLM (AGENTS.md I4).

Layout follows the OneATS Grid Designer convention, so an operator who knows the
existing HMI reads this without relearning anything.

One bay, drawn normally (busbars above, terminal below)::

    C21 ═════╤═════════════════   main busbar 1
             │                    -1 has its OWN drop, in its own lane
    C22 ═════╪═══╤═════════════   main busbar 2   (crossing, no dot)
            ◆-1  │
             │  ◆-2
             └─┬─┘                fork bar = the busbar-side node
             [271]                breaker
               │
             ◆-7  ⏚
               │
    C29 ═══╤═══╪═══════════════   transfer busbar
          ◆-9  │                  (crossing, no dot)
               ○                  the line leaves here

Two rules earn their keep here, and both are safety rules, not style:

1.  **Every conductor that connects to a busbar gets its own x lane, and the
    connection is marked with a junction dot.** Drawing -1 and -2 on the same
    vertical made the spine touch both rails at the same point, so the picture
    showed a continuous path through both busbars no matter what the isolators
    were doing. A crossing without a dot means "no connection" — the standard
    single-line convention, and the only way the reader can tell a real path
    from a drawn one.

2.  **The transfer busbar sits between the bay and its terminal**, because that
    is where it connects electrically: `-9` bypasses the breaker and feeds the
    line directly (see the CheckLiveState Lua quoted in T1_LINE.yaml).

`layout_station` stacks the voltage levels into one drawing, highest at the top,
and mirrors the top one so the two main-busbar groups face each other across the
middle — the arrangement of the station's own Grid Designer sheet.

Geometry comes from the bay template (slot order and side), so a new bay type is
a YAML file, not a change here.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from blackinterface.domain.models import (
    Bay,
    Device,
    DeviceRole,
    NodeKind,
    Quality,
    StationGraph,
    SwitchState,
)
from blackinterface.domain.templates import BayTemplate, TemplateRegistry, default_registry

# ---- geometry constants (SVG user units) -----------------------------------
MARGIN_X = 100.0
COLUMN_PITCH = 210.0
RAIL_TOP = 70.0
RAIL_GAP = 56.0  # between the main busbars
RAIL_MARGIN = 78.0  # how far a rail extends past the outermost bay
SPINE_GAP = 96.0  # last main rail -> first node of the bay spine
ROW_HEIGHT = 62.0  # between consecutive spine nodes
TRANSFER_GAP = 74.0  # deepest spine node -> transfer busbar rail
TERMINAL_DROP = 58.0  # transfer rail -> the external terminal
STUB = 32.0  # how far from its rail a busbar selector sits
LANE = 34.0  # x offset of a selector's private drop to its rail
SIDE_OFFSET = 54.0  # x offset for a side-mounted earth switch
LABEL_BLOCK = 66.0  # room past the terminal for the bay caption
SECTION_GAP = 104.0  # between two voltage levels in the station drawing

#: EVN numbering: busbar index 9 is the transfer busbar.
TRANSFER_INDEX = 9

SELECTOR_ROLES = (DeviceRole.BUSBAR_SELECTOR, DeviceRole.TRANSFER_SELECTOR)

_KV = re.compile(r"([\d.]+)")


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Point(Frozen):
    x: float
    y: float


class RailView(Frozen):
    busbar_id: str
    label: str
    y: float
    x1: float
    x2: float
    is_live: bool | None = None
    quality: Quality = Quality.MISSING
    inferred: bool = False
    transfer: bool = False


class SymbolView(Frozen):
    device_id: str
    bay_id: str
    ln: str
    role: DeviceRole
    label: str
    x: float
    y: float
    state: SwitchState
    quality: Quality
    #: True when the band is mirrored, so the ground hatch points the other way.
    flipped: bool = False


class EdgeView(Frozen):
    id: str
    points: tuple[Point, ...]
    device_id: str | None = None  # edge belongs to this device's terminal


class JunctionView(Frozen):
    """A real connection to a busbar. Drawn as a dot; a crossing has none."""

    id: str
    x: float
    y: float


class TerminalView(Frozen):
    """Where the bay leaves the station: a line, a transformer, a feeder."""

    node_id: str
    label: str
    x: float
    y: float
    bay_type: str
    flipped: bool = False


class ColumnView(Frozen):
    bay_id: str
    label: str
    caption: str  # EVN designation of the bay's breaker, e.g. "271"
    bay_type: str
    template_id: str | None
    x: float
    top: float
    bottom: float
    label_y: float  # where the bay caption block starts
    flipped: bool = False  # caption reads away from the diagram
    issue_count: int = 0
    error_count: int = 0


class DiagramView(Frozen):
    voltage_level: str
    width: float
    height: float
    rails: tuple[RailView, ...] = ()
    columns: tuple[ColumnView, ...] = ()
    symbols: tuple[SymbolView, ...] = ()
    edges: tuple[EdgeView, ...] = ()
    terminals: tuple[TerminalView, ...] = ()
    junctions: tuple[JunctionView, ...] = ()


class SectionView(Frozen):
    """One voltage level's band inside the station drawing."""

    voltage_level: str
    top: float
    bottom: float
    flipped: bool
    bay_count: int


class StationView(Frozen):
    """Every voltage level in one drawing, the way an SLD is normally read."""

    name: str
    width: float
    height: float
    sections: tuple[SectionView, ...] = ()
    rails: tuple[RailView, ...] = ()
    columns: tuple[ColumnView, ...] = ()
    symbols: tuple[SymbolView, ...] = ()
    edges: tuple[EdgeView, ...] = ()
    terminals: tuple[TerminalView, ...] = ()
    junctions: tuple[JunctionView, ...] = ()


# ----------------------------------------------------------------- one level
def layout_voltage_level(
    graph: StationGraph,
    voltage_level: str,
    registry: TemplateRegistry | None = None,
) -> DiagramView:
    """Lay out every bay at one voltage level."""
    registry = registry or default_registry()

    busbars = [b for b in graph.busbars if b.voltage_level == voltage_level]
    main = sorted((b for b in busbars if b.index != TRANSFER_INDEX), key=lambda b: b.index)
    transfer = next((b for b in busbars if b.index == TRANSFER_INDEX), None)

    rail_y = {b.node_id: RAIL_TOP + i * RAIL_GAP for i, b in enumerate(main)}
    spine_top = max(rail_y.values(), default=RAIL_TOP) + SPINE_GAP

    bays = [
        b
        for b in graph.bays
        if b.voltage_level == voltage_level and b.template_id and graph.devices_of(b.id)
    ]
    templates = {b.id: registry.by_id(b.template_id or "") for b in bays}

    # The transfer rail goes below the deepest bay spine, so `-9` always has
    # room between the node it feeds and its own busbar.
    depth = max((len(t.nodes) for t in templates.values() if t), default=1)
    spine_bottom = spine_top + (depth - 1) * ROW_HEIGHT
    if transfer is not None:
        rail_y[transfer.node_id] = spine_bottom + TRANSFER_GAP
    terminal_y = max(rail_y.values(), default=spine_bottom) + TERMINAL_DROP

    symbols: list[SymbolView] = []
    edges: list[EdgeView] = []
    columns: list[ColumnView] = []
    terminals: list[TerminalView] = []
    junctions: list[JunctionView] = []

    for i, bay in enumerate(bays):
        template = templates[bay.id]
        if template is None:
            continue
        _layout_bay(
            graph=graph,
            bay=bay,
            template=template,
            column_x=MARGIN_X + i * COLUMN_PITCH,
            spine_top=spine_top,
            rail_y=rail_y,
            terminal_y=terminal_y,
            symbols=symbols,
            edges=edges,
            columns=columns,
            terminals=terminals,
            junctions=junctions,
        )

    width = MARGIN_X * 2 + max(len(bays) - 1, 0) * COLUMN_PITCH + MARGIN_X
    height = max((c.label_y for c in columns), default=terminal_y) + LABEL_BLOCK
    rails = tuple(
        RailView(
            busbar_id=b.id,
            label=b.name,
            y=rail_y[b.node_id],
            x1=MARGIN_X - RAIL_MARGIN,
            x2=width - MARGIN_X + RAIL_MARGIN,
            is_live=b.is_live.value if isinstance(b.is_live.value, bool) else None,
            quality=b.is_live.quality,
            inferred=b.inferred,
            transfer=b.index == TRANSFER_INDEX,
        )
        for b in sorted(busbars, key=lambda bb: rail_y[bb.node_id])
    )
    return DiagramView(
        voltage_level=voltage_level,
        width=width,
        height=height,
        rails=rails,
        columns=tuple(columns),
        symbols=tuple(symbols),
        edges=tuple(edges),
        terminals=tuple(terminals),
        junctions=tuple(junctions),
    )


def _layout_bay(
    *,
    graph: StationGraph,
    bay: Bay,
    template: BayTemplate,
    column_x: float,
    spine_top: float,
    rail_y: dict[str, float],
    terminal_y: float,
    symbols: list[SymbolView],
    edges: list[EdgeView],
    columns: list[ColumnView],
    terminals: list[TerminalView],
    junctions: list[JunctionView],
) -> None:
    node_kind = {n.id: n.kind for n in graph.nodes}

    # The template declares its nodes top to bottom; that is the bay spine.
    node_y: dict[str, float] = {
        f"{bay.id}.{node.id}": spine_top + rank * ROW_HEIGHT
        for rank, node in enumerate(template.nodes)
    }
    node_y.update(rail_y)

    devices = {d.ln: d for d in graph.devices_of(bay.id)}
    lane_x = _assign_lanes(template, devices, rail_y, spine_top, column_x)
    lowest = spine_top

    for slot in template.slots:
        device = devices.get(slot.ln)
        if device is None:
            continue
        ends = [t.node_id for t in device.terminals]
        ys = [node_y.get(n) for n in ends]

        if slot.role in SELECTOR_ROLES:
            y = _selector_y(ends, ys, rail_y, spine_top)
            x = lane_x.get(slot.ln, column_x)
        elif slot.role is DeviceRole.EARTH_SWITCH:
            attached = next(
                (y for n, y in zip(ends, ys, strict=True) if node_kind.get(n) != NodeKind.EARTH),
                None,
            )
            y = attached if attached is not None else spine_top
            x = column_x + {"left": -SIDE_OFFSET, "right": SIDE_OFFSET}.get(slot.side, 0.0)
        else:
            known = [y for y in ys if y is not None]
            y = sum(known) / len(known) if known else spine_top
            x = column_x

        symbols.append(
            SymbolView(
                device_id=device.id,
                bay_id=bay.id,
                ln=device.ln,
                role=device.role,
                label=device.short_name or device.name or device.ln,
                x=x,
                y=y,
                state=device.state,
                quality=device.position.quality,
            )
        )
        lowest = max(lowest, y)
        edges.extend(_edges_for(device, x, y, column_x, node_y, node_kind))
        junctions.extend(
            JunctionView(id=f"{device.id}.{t.seq}", x=x, y=rail_y[t.node_id])
            for t in device.terminals
            if t.node_id in rail_y
        )

    # External terminal: the tail runs from its node past the transfer rail.
    for node in template.nodes:
        if node.kind is not NodeKind.EXTERNAL:
            continue
        node_id = f"{bay.id}.{node.id}"
        y = node_y[node_id]
        edges.append(
            EdgeView(
                id=f"{node_id}.tail",
                points=(Point(x=column_x, y=y), Point(x=column_x, y=terminal_y)),
            )
        )
        terminals.append(
            TerminalView(
                node_id=node_id,
                label=node.label,
                x=column_x,
                y=terminal_y,
                bay_type=str(bay.bay_type),
            )
        )
        lowest = max(lowest, terminal_y)

    breaker = devices.get("XCBR1")
    errors = sum(1 for issue in bay.issues if issue.severity == "error")
    bottom = lowest + 24.0
    columns.append(
        ColumnView(
            bay_id=bay.id,
            label=bay.name,
            caption=breaker.name if breaker else "",
            bay_type=str(bay.bay_type),
            template_id=bay.template_id,
            x=column_x,
            top=RAIL_TOP,
            bottom=bottom,
            label_y=bottom + 22.0,
            issue_count=len(bay.issues),
            error_count=errors,
        )
    )


def _assign_lanes(
    template: BayTemplate,
    devices: dict[str, Device],
    rail_y: dict[str, float],
    spine_top: float,
    column_x: float,
) -> dict[str, float]:
    """Give every busbar-connected isolator its own vertical, alternating sides.

    Two isolators sharing a lane would put two rail connections on one line, and
    the drawing could no longer distinguish "connected to busbar 1" from
    "connected to busbar 2". Isolators reaching up to the main busbars and those
    reaching down to the transfer busbar are numbered separately, because their
    drops never overlap.
    """
    above: list[str] = []
    below: list[str] = []
    for slot in template.slots:
        device = devices.get(slot.ln)
        if device is None or slot.role not in SELECTOR_ROLES:
            continue
        rail = next((t.node_id for t in device.terminals if t.node_id in rail_y), None)
        if rail is None:
            continue
        (above if rail_y[rail] < spine_top else below).append(slot.ln)

    lanes: dict[str, float] = {}
    for group in (above, below):
        for i, ln in enumerate(group):
            side = -1.0 if i % 2 == 0 else 1.0
            lanes[ln] = column_x + side * LANE * (i // 2 + 1)
    return lanes


def _selector_y(
    ends: list[str],
    ys: list[float | None],
    rail_y: dict[str, float],
    fallback: float,
) -> float:
    """A selector sits on a short stub off its own rail, on the bay's side of it.

    Main busbars are above the bay, the transfer busbar below it, so the stub
    direction depends on which side the node it feeds is on.
    """
    rail = next((y for n, y in zip(ends, ys, strict=True) if n in rail_y), None)
    if rail is None:
        return fallback
    other = next(
        (y for n, y in zip(ends, ys, strict=True) if n not in rail_y and y is not None), None
    )
    if other is None:
        return rail + STUB
    return rail + STUB if other > rail else rail - STUB


def _edges_for(
    device: Device,
    x: float,
    y: float,
    column_x: float,
    node_y: dict[str, float],
    node_kind: dict[str, NodeKind],
) -> list[EdgeView]:
    """One polyline per terminal, from the symbol to the node it attaches to."""
    result = []
    for terminal in device.terminals:
        kind = node_kind.get(terminal.node_id)
        if kind is NodeKind.EARTH:
            result.append(
                EdgeView(
                    id=f"{device.id}.{terminal.seq}",
                    device_id=device.id,
                    points=(Point(x=x, y=y), Point(x=x, y=y + 24.0)),
                )
            )
            continue
        target = node_y.get(terminal.node_id)
        if target is None:
            continue
        points = (
            (Point(x=x, y=y), Point(x=x, y=target))
            if x == column_x
            else (Point(x=x, y=y), Point(x=x, y=target), Point(x=column_x, y=target))
        )
        result.append(
            EdgeView(id=f"{device.id}.{terminal.seq}", device_id=device.id, points=points)
        )
    return result


# ------------------------------------------------------------- whole station
def layout_station(
    graph: StationGraph,
    registry: TemplateRegistry | None = None,
) -> StationView:
    """Stack every voltage level into one drawing, highest voltage at the top.

    The topmost band is mirrored: its busbars end up at the bottom of the band,
    facing the next level's busbars across the middle, and its outgoing lines
    point up and away. That is how the station's own Grid Designer sheet is
    drawn, and how a substation single-line diagram is normally read.

    The transformer coupling two bands is deliberately NOT drawn as a conductor.
    The DataServer carries no connectivity, so we have no evidence of which HV
    bay pairs with which LV bay; drawing that line would be inventing a current
    path (AGENTS.md I3). Each transformer bay ends in a transformer terminal
    symbol instead.
    """
    registry = registry or default_registry()
    levels = sorted(graph.voltage_levels, key=_kilovolts, reverse=True)

    sections: list[SectionView] = []
    rails: list[RailView] = []
    columns: list[ColumnView] = []
    symbols: list[SymbolView] = []
    edges: list[EdgeView] = []
    terminals: list[TerminalView] = []
    junctions: list[JunctionView] = []

    top = 0.0
    width = 0.0
    drawn = 0
    for level in levels:
        view = layout_voltage_level(graph, level, registry)
        if not view.columns:
            continue
        flip = drawn == 0 and len(levels) > 1
        band = view.height
        place = _placer(top, band, flip)

        rails.extend(r.model_copy(update={"y": place(r.y)}) for r in view.rails)
        symbols.extend(
            s.model_copy(update={"y": place(s.y), "flipped": flip}) for s in view.symbols
        )
        terminals.extend(
            t.model_copy(update={"y": place(t.y), "flipped": flip}) for t in view.terminals
        )
        junctions.extend(j.model_copy(update={"y": place(j.y)}) for j in view.junctions)
        edges.extend(
            e.model_copy(update={"points": tuple(Point(x=p.x, y=place(p.y)) for p in e.points)})
            for e in view.edges
        )
        for column in view.columns:
            ends = sorted((place(column.top), place(column.bottom)))
            columns.append(
                column.model_copy(
                    update={
                        "top": ends[0],
                        "bottom": ends[1],
                        "label_y": place(column.label_y),
                        "flipped": flip,
                    }
                )
            )
        sections.append(
            SectionView(
                voltage_level=level,
                top=top,
                bottom=top + band,
                flipped=flip,
                bay_count=len(view.columns),
            )
        )
        width = max(width, view.width)
        top += band + SECTION_GAP
        drawn += 1

    return StationView(
        name=graph.name,
        width=width,
        height=max(top - SECTION_GAP, 0.0),
        sections=tuple(sections),
        rails=tuple(rails),
        columns=tuple(columns),
        symbols=tuple(symbols),
        edges=tuple(edges),
        terminals=tuple(terminals),
        junctions=tuple(junctions),
    )


def _placer(top: float, band: float, flip: bool) -> Callable[[float], float]:
    """Map a band-local y onto the station canvas, mirroring it if asked."""

    def place(y: float) -> float:
        return top + (band - y) if flip else top + y

    return place


def _kilovolts(voltage_level: str) -> float:
    """`"220kV"` -> 220.0. An unparseable level sorts last but still gets drawn."""
    match = _KV.search(voltage_level)
    return float(match.group(1)) if match else 0.0


__all__ = [
    "ColumnView",
    "DiagramView",
    "EdgeView",
    "JunctionView",
    "Point",
    "RailView",
    "SectionView",
    "StationView",
    "SymbolView",
    "TerminalView",
    "layout_station",
    "layout_voltage_level",
]
