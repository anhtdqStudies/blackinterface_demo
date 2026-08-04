"""Turn a station graph into coordinates. Deterministic, no LLM (AGENTS.md I4).

One view per voltage level. Busbars are horizontal rails; each bay is a
vertical column hanging below them. Busbar selectors sit on short stubs that
reach up to their own rail, which is how a single-line diagram is actually
drawn — and it makes "which busbar is this bay on right now?" readable at a
glance once the stubs are coloured by position.

The geometry comes from the bay template (slot order and side), so a new bay
type is a YAML file, not a change here.
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
from blackinterface.domain.templates import TemplateRegistry, default_registry

# ---- geometry constants (SVG user units) -----------------------------------
MARGIN_X = 90.0
COLUMN_PITCH = 190.0
RAIL_TOP = 60.0
RAIL_GAP = 62.0
RAIL_MARGIN = 70.0
STUB = 34.0  # how far below its rail a busbar selector sits
SPINE_GAP = 140.0  # from the lowest rail down to the first internal node
ROW_HEIGHT = 62.0
SIDE_OFFSET = 46.0  # x offset for a side-mounted earth switch
TERMINAL_DROP = 56.0  # tail below the last node, for the external terminal

#: Rails top to bottom: transfer busbar above the two main busbars.
RAIL_ORDER = (9, 1, 2)

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


def _rail_y(index: int) -> float:
    try:
        rank = RAIL_ORDER.index(index)
    except ValueError:
        rank = len(RAIL_ORDER)
    return RAIL_TOP + rank * RAIL_GAP


def layout_voltage_level(
    graph: StationGraph,
    voltage_level: str,
    registry: TemplateRegistry | None = None,
) -> DiagramView:
    """Lay out every bay at one voltage level."""
    registry = registry or default_registry()
    busbars = sorted(
        (b for b in graph.busbars if b.voltage_level == voltage_level),
        key=lambda b: _rail_y(b.index),
    )
    rail_y = {b.node_id: _rail_y(b.index) for b in busbars}
    lowest_rail = max(rail_y.values(), default=RAIL_TOP)

    bays = [
        b
        for b in graph.bays
        if b.voltage_level == voltage_level and b.template_id and graph.devices_of(b.id)
    ]

    symbols: list[SymbolView] = []
    edges: list[EdgeView] = []
    columns: list[ColumnView] = []
    terminals: list[TerminalView] = []

    for i, bay in enumerate(bays):
        column_x = MARGIN_X + i * COLUMN_PITCH
        _layout_bay(
            graph, bay, column_x, lowest_rail, rail_y, registry, symbols, edges, columns, terminals
        )

    width = MARGIN_X * 2 + max(len(bays) - 1, 0) * COLUMN_PITCH + MARGIN_X
    height = max((c.bottom for c in columns), default=lowest_rail) + 60.0
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
        )
        for b in busbars
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
    graph: StationGraph,
    bay: Bay,
    column_x: float,
    lowest_rail: float,
    rail_y: dict[str, float],
    registry: TemplateRegistry,
    symbols: list[SymbolView],
    edges: list[EdgeView],
    columns: list[ColumnView],
    terminals: list[TerminalView],
) -> None:
    template = registry.by_id(bay.template_id or "")
    if template is None:
        return

    node_kind = {n.id: n.kind for n in graph.nodes}

    # Internal/external nodes stack down the spine in template declaration order.
    node_y: dict[str, float] = {
        f"{bay.id}.{node.id}": lowest_rail + SPINE_GAP + rank * ROW_HEIGHT
        for rank, node in enumerate(template.nodes)
    }
    node_y.update(rail_y)

    devices = {d.ln: d for d in graph.devices_of(bay.id)}
    lowest = lowest_rail

    for slot in template.slots:
        device = devices.get(slot.ln)
        if device is None:
            continue
        ends = [t.node_id for t in device.terminals]
        ys = [node_y.get(n) for n in ends]

        if slot.role in SELECTOR_ROLES:
            rail = next((y for n, y in zip(ends, ys, strict=True) if n in rail_y), None)
            y = (rail if rail is not None else lowest_rail) + STUB
        elif slot.role is DeviceRole.EARTH_SWITCH:
            attached = next(
                (y for n, y in zip(ends, ys, strict=True) if node_kind.get(n) != NodeKind.EARTH),
                None,
            )
            y = attached if attached is not None else lowest_rail + SPINE_GAP
        else:
            known = [y for y in ys if y is not None]
            y = sum(known) / len(known) if known else lowest_rail + SPINE_GAP

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

    # External terminal: a tail below the last node in the spine.
    for node in template.nodes:
        if node.kind is not NodeKind.EXTERNAL:
            continue
        node_id = f"{bay.id}.{node.id}"
        y = node_y[node_id]
        edges.append(
            EdgeView(
                id=f"{node_id}.tail",
                points=(Point(x=column_x, y=y), Point(x=column_x, y=y + TERMINAL_DROP)),
            )
        )
        terminals.append(
            TerminalView(node_id=node_id, label=node.label, x=column_x, y=y + TERMINAL_DROP)
        )
        lowest = max(lowest, y + TERMINAL_DROP)

    errors = sum(1 for issue in bay.issues if issue.severity == "error")
    columns.append(
        ColumnView(
            bay_id=bay.id,
            label=bay.name,
            bay_type=str(bay.bay_type),
            template_id=bay.template_id,
            x=column_x,
            top=RAIL_TOP,
            bottom=lowest + 30.0,
            issue_count=len(bay.issues),
            error_count=errors,
        )
    )


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
                    points=(Point(x=x, y=y), Point(x=x, y=y + 26.0)),
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
