/**
 * The single operator layout (ADR-0018). **This is the only file allowed to
 * define one** — `tools/check.py` enforces that.
 *
 * Conversation-first: chat column left, workspace tabs right (SLD is a tab).
 * Splitter sizes are starting points — overwritten from `localStorage` once
 * somebody has dragged anything.
 */
import type { Layout, PaneKind, Pane } from './panes'

/** Ids are the kind, because no slot shows the same kind twice. */
function pane(kind: PaneKind, params?: Readonly<Record<string, unknown>>): Pane {
  return params ? { id: kind, kind, params } : { id: kind, kind }
}

const WORKSPACE_TABS = [
  'sld',
  'state',
  'measurements',
  'energization',
  'anomalies',
  'evidence',
] as const satisfies readonly PaneKind[]

export type WorkspaceTabKind = (typeof WORKSPACE_TABS)[number]

export const WORKSPACE_TAB_KINDS: readonly WorkspaceTabKind[] = WORKSPACE_TABS

export const DEFAULT_TAB: WorkspaceTabKind = 'sld'

export function isWorkspaceTab(value: string): value is WorkspaceTabKind {
  return (WORKSPACE_TAB_KINDS as readonly string[]).includes(value)
}

/**
 * Operator workspace — chat left, tabbed panes right (ADR-0018, 2026-08-10).
 */
export const OPERATOR_LAYOUT: Layout = {
  cols: [
    {
      size: 42,
      rows: [{ size: 100, pane: pane('chat', { chrome: 'minimal' }) }],
    },
    {
      size: 58,
      rows: [
        {
          size: 100,
          slot: {
            kind: 'tabs',
            panes: WORKSPACE_TABS.map((kind) => pane(kind, { chrome: 'minimal' })),
          },
        },
      ],
    },
  ],
}
