/**
 * The three shipped layouts (ADR-0014 §3). **This is the only file allowed to
 * define one** — `tools/check.py` enforces that, because a layout defined inside
 * a view is a layout nobody can find when it needs changing.
 *
 * There is no free-form dock editor and there will not be one (ADR-0014,
 * rejected alternative B): building a layout editor is building a different
 * product. Presets plus drag-to-resize cover what an operator actually does, and
 * the resize is remembered per preset.
 *
 * Sizes are percentages. They are starting points — the splitter overwrites them
 * from `localStorage` once somebody has dragged anything.
 */
import type { Layout, PaneKind } from './panes'

/** Ids are the kind, because no preset shows the same kind twice. */
function pane(kind: PaneKind, params?: Readonly<Record<string, unknown>>) {
  return params ? { id: kind, kind, params } : { id: kind, kind }
}

/** Scope inspector — accordion sections, minimal outer chrome (screens.md §3.1). */
const inspector = pane('inspector', { chrome: 'minimal' })

/**
 * Watching the station. SLD full height left; one inspector column right.
 */
const monitor: Layout = {
  cols: [
    { size: 72, rows: [{ size: 100, pane: pane('sld') }] },
    { size: 28, rows: [{ size: 100, pane: inspector }] },
  ],
}

/**
 * Asking, with the diagram out of the way entirely.
 */
const chat: Layout = {
  cols: [{ size: 100, rows: [{ size: 100, pane: pane('chat') }] }],
}

/** Working out what happened: ask on the left, SLD + inspector on the right. */
const incident: Layout = {
  cols: [
    { size: 38, rows: [{ size: 100, pane: pane('chat') }] },
    {
      size: 62,
      rows: [
        { size: 48, pane: pane('sld') },
        { size: 52, pane: inspector },
      ],
    },
  ],
}

export const PRESETS = { monitor, chat, incident } as const

export type PresetName = keyof typeof PRESETS

export const PRESET_NAMES = Object.keys(PRESETS) as PresetName[]

export const DEFAULT_PRESET: PresetName = 'monitor'

export function isPresetName(value: string): value is PresetName {
  return Object.hasOwn(PRESETS, value)
}

/**
 * The layout for a name — `DEFAULT_PRESET` for anything unrecognised.
 */
export function layoutFor(name: string | null | undefined): Layout {
  return PRESETS[name && isPresetName(name) ? name : DEFAULT_PRESET]
}

/** Label key per preset, spelled out so the i18n check can see them. */
export const PRESET_LABEL_KEY: Readonly<Record<PresetName, string>> = {
  monitor: 'preset.monitor',
  chat: 'preset.chat',
  incident: 'preset.incident',
}
