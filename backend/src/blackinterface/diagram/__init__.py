"""L6 — Diagram engine: graph -> layout -> ViewModel -> SVG.

Layout is GENERATED, never hand-drawn (ADR-0003).
  * bay  -> column,  busbar -> horizontal rail
  * devices stack vertically following the bay template slot order
  * engineer overrides are stored as a SPARSE PATCH LAYER
    (e.g. {bay_id: {x_order: 3}}), never as absolute coordinates,
    so re-import does not destroy manual corrections.

Views are rendered on demand and scoped: bay view, busbar-section view,
source-to-point path view, whole-station overview.
"""
