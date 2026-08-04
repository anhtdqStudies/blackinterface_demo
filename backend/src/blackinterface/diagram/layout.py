"""Turn a station graph into coordinates. Deterministic, no LLM (AGENTS.md I4).

Layout follows the OneATS Grid Designer convention, so an operator who knows
the existing HMI reads this without relearning anything:

    C21 ═════════════╤═══════   main busbar 1
    C22 ═════════╤═══╪═══════   main busbar 2
                 │   │
                [-2][-1]        busbar selectors, on stubs at their own rail
                 └─┬─┘
                 [271]          breaker
                   │
                 [-7]  ⏚        line disconnector + earth switches
                   │
    C29 ═══════╤═══╪═══════     transfer busbar, on the terminal side
              [-9] │
                   ○            the line leaves here

The transfer busbar sits between the bay and its terminal because that is where
it connects electrically: `-9` bypasses the breaker and feeds the line directly.
Putting it beside the main busbars would draw a line that does not exist.

Geometry comes from the bay template (slot order and side), so a new bay type is
a YAML file, not a change here.
"""

from __future__ import annotations

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
COLUMN_PITCH = 200.0
RAIL_TOP = 70.0
RAIL_GAP = 56.0  # between the main busbars
RAIL_MARGIN = 78.0  # how far a rail extends past the outermost bay
SPINE_GAP = 96.0  # last main rail -> first node of the bay spine
ROW_HEIGHT = 62.0  # between consecutive spine nodes
TRANSFER_GAP = 74.0  # deepest spine node -> transfer busbar rail
TERMINAL_DROP = 58.0  # transfer rail -> the external terminal
STUB = 32.0  # how far from its rail a busbar selector sits
SIDE_OFFSET = 48.0  # x offset for a side-mounted earth switch
LABEL_BLOCK = 66.0  # room under the terminal for the bay caption

#: EVN numbering: busbar index 9 is the transfer busbar.
TRANSFER_INDEX = 9

SELECTOR_ROLES = (DeviceRole.BUSBAR_SELECTOR, DeviceRole.TRANSFER_SELECTOR)


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


class EdgeView(Frozen):
    id: str
    points: tuple[Point, ...]
    device_id: str | None = None  # edge belongs to this device's terminal


class TerminalView(Frozen):
    """Where the bay leaves the station: a line, a transformer, a feeder."""

    node_id: str
    label: str
    x: float
    y: float


class ColumnView(Frozen):
    bay_id: str
    label: str
    caption: str  # EVN designation of the bay's breaker, e.g. "271"
    bay_type: str
    template_id: str | None
    x: float
    top: float
    bottom: float
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
        )

    width = MARGIN_X * 2 + max(len(bays) - 1, 0) * COLUMN_PITCH + MARGIN_X
    height = max((c.bottom for c in columns), default=terminal_y) + LABEL_BLOCK
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
) -> None:
    node_kind = {n.id: n.kind for n in graph.nodes}

    # The template declares its nodes top to bottom; that is the bay spine.
    node_y: dict[str, float] = {
        f"{bay.id}.{node.id}": spine_top + rank * ROW_HEIGHT
        for rank, node in enumerate(template.nodes)
    }
    node_y.update(rail_y)

    devices = {d.ln: d for d in graph.devices_of(bay.id)}
    lowest = spine_top

    for slot in template.slots:
        device = devices.get(slot.ln)
        if device is None:
            continue
        ends = [t.node_id for t in device.terminals]
        ys = [node_y.get(n) for n in ends]

        if slot.role in SELECTOR_ROLES:
            y = _selector_y(ends, ys, rail_y, spine_top)
        elif slot.role is DeviceRole.EARTH_SWITCH:
            attached = next(
                (y for n, y in zip(ends, ys, strict=True) if node_kind.get(n) != NodeKind.EARTH),
                None,
            )
            y = attached if attached is not None else spine_top
        else:
            known = [y for y in ys if y is not None]
            y = sum(known) / len(known) if known else spine_top

        x = column_x + {"left": -SIDE_OFFSET, "right": SIDE_OFFSET}.get(slot.side, 0.0)
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
        terminals.append(TerminalView(node_id=node_id, label=node.label, x=column_x, y=terminal_y))
        lowest = max(lowest, terminal_y)

    breaker = devices.get("XCBR1")
    errors = sum(1 for issue in bay.issues if issue.severity == "error")
    columns.append(
        ColumnView(
            bay_id=bay.id,
            label=bay.name,
            caption=breaker.name if breaker else "",
            bay_type=str(bay.bay_type),
            template_id=bay.template_id,
            x=column_x,
            top=RAIL_TOP,
            bottom=lowest + 24.0,
            issue_count=len(bay.issues),
            error_count=errors,
        )
    )


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


__all__ = [
    "ColumnView",
    "DiagramView",
    "EdgeView",
    "Point",
    "RailView",
    "SymbolView",
    "TerminalView",
    "layout_voltage_level",
]
