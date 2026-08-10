/**
 * The pane contract (ADR-0014 §3, ADR-0018, frontend-architecture.md §3).
 *
 * A layout is **data**, not code. That single choice buys four things at once:
 * it survives a reload in `localStorage`, it travels in a URL, the agent can
 * *propose* one because proposing is just emitting an object, and it can be
 * tested without a browser.
 *
 * The register below is the whole extension point. Adding a kind of pane is one
 * line here plus one component — never an edit to `PaneHost`. If `PaneHost` ever
 * needs a `v-if` on `kind` to show something, this contract has failed, and
 * `tools/check.py` asserts that it has not.
 */
import { defineAsyncComponent, type Component } from 'vue'
import type { ScopeRef } from '@/scope'

export const PANE_KINDS = [
  'sld',
  'state',
  'measurements',
  'energization',
  'anomalies',
  'evidence',
  'chat',
  'connections',
  'coverage',
  'model-issues',
  'binding',
] as const

export type PaneKind = (typeof PANE_KINDS)[number]

export interface Pane {
  /** Stable across renders so Vue keeps the same DOM when the layout redraws. */
  readonly id: string
  readonly kind: PaneKind
  /**
   * **Absent means "follow the workspace scope"** — and absent is the default.
   *
   * This is the one place the contract departs from ADR-0014, which made scope
   * mandatory on every pane. The rule that matters (screens.md §1) is *clicking a
   * bay makes the whole screen talk about that bay*. If every pane carried its
   * own scope, one click would have to update N panes, and forgetting one leaves
   * the screen showing two different bays **without saying so** — exactly the
   * failure ADR-0010 exists to prevent.
   *
   * Setting it is therefore a deliberate act: *"pin bay D03 in this cell while I
   * go look elsewhere"*, which is what people actually need during an incident.
   * A pinned pane must say it is pinned, or it becomes a trap.
   */
  readonly scope?: ScopeRef
  readonly params?: Readonly<Record<string, unknown>>
}

/** Tab group in the workspace right column (ADR-0018). */
export interface LayoutTabs {
  readonly kind: 'tabs'
  readonly panes: readonly Pane[]
}

export type LayoutRow =
  | { readonly size: number; readonly pane: Pane }
  | { readonly size: number; readonly slot: LayoutTabs }

export interface LayoutColumn {
  /** Percent of the workspace width. */
  readonly size: number
  readonly rows: readonly LayoutRow[]
}

export interface Layout {
  readonly cols: readonly LayoutColumn[]
}

export function isPaneKind(value: string): value is PaneKind {
  return (PANE_KINDS as readonly string[]).includes(value)
}

/** Every pane receives exactly these props. Nothing else is passed by `PaneHost`. */
export interface PaneProps {
  readonly pane: Pane
  /** Already resolved: the pin if there is one, otherwise the workspace scope. */
  readonly scope: ScopeRef
}

/**
 * Not yet built. Kinds pointing here render "arrives in a later phase" rather
 * than a blank cell, so a layout can name a pane before the pane exists.
 * `binding` is the remaining one.
 */
const later = defineAsyncComponent(() => import('./PaneLater.vue'))

/**
 * Kind → component. **The only branch on `kind` in the whole frontend.**
 *
 * Async on purpose: a workspace shows three or four kinds, not eleven, so the
 * rest stay out of the first download.
 */
export const PANE_COMPONENTS: Readonly<Record<PaneKind, Component>> = {
  sld: defineAsyncComponent(() => import('@/features/station/SldPane.vue')),
  state: defineAsyncComponent(() => import('@/features/monitoring/StatePane.vue')),
  measurements: defineAsyncComponent(() => import('@/features/monitoring/MeasurementPane.vue')),
  energization: defineAsyncComponent(
    () => import('@/features/monitoring/EnergizationPane.vue'),
  ),
  evidence: defineAsyncComponent(() => import('@/features/monitoring/EvidencePane.vue')),
  coverage: defineAsyncComponent(() => import('@/features/engineer/CoveragePane.vue')),
  'model-issues': defineAsyncComponent(() => import('@/features/engineer/ModelIssuesPane.vue')),
  chat: defineAsyncComponent(() => import('@/features/assistant/ChatPane.vue')),
  binding: later,
  anomalies: defineAsyncComponent(() => import('@/features/monitoring/AnomaliesPane.vue')),
  connections: defineAsyncComponent(() => import('@/features/engineer/ConnectionsPane.vue')),
}

/**
 * Title key per kind, written out in full rather than built as `pane.${kind}`.
 *
 * A template literal would hide every one of these from a static scan, and
 * `check.py` is what keeps `vi` and `en` from drifting apart. A missing title is
 * a pane with no name on it — cheap to prevent, annoying to notice later.
 */
export const PANE_TITLE_KEY: Readonly<Record<PaneKind, string>> = {
  sld: 'pane.sld',
  state: 'pane.state',
  measurements: 'pane.measurements',
  energization: 'pane.energization',
  anomalies: 'pane.anomalies',
  evidence: 'pane.evidence',
  chat: 'pane.chat',
  connections: 'pane.connections',
  coverage: 'pane.coverage',
  'model-issues': 'pane.modelIssues',
  binding: 'pane.binding',
}

/** A pane carrying its own scope is pinned; it ignores where the workspace went. */
export function isPinned(pane: Pane): boolean {
  return pane.scope !== undefined
}

function rowPanes(row: LayoutRow): Pane[] {
  if ('pane' in row) return [row.pane]
  return [...row.slot.panes]
}

/** Every pane in a layout, in reading order. */
export function panesOf(layout: Layout): Pane[] {
  return layout.cols.flatMap((col) => col.rows.flatMap(rowPanes))
}

export function isLayoutRowPane(
  row: LayoutRow,
): row is { readonly size: number; readonly pane: Pane } {
  return 'pane' in row
}

export function isLayoutRowTabs(
  row: LayoutRow,
): row is { readonly size: number; readonly slot: LayoutTabs } {
  return 'slot' in row
}
