import type { LiveState, Quality, SwitchState } from '@/api/client'

/**
 * STATION palette only (ADR-0014 section 2). Nothing here may paint the
 * application's own health — that is `ui/StatusDot.vue`, which uses a separate
 * palette on purpose, because red once meant both "breaker closed" and "we lost
 * the connection".
 *
 * OneATS Grid Designer convention: red = closed, green = open on a **device**;
 * blue = energised, green = de-energised on a **conductor**. Green therefore
 * means two different things depending on what it paints — operators here
 * already read it that way, so we match rather than invent.
 *
 * UNDETERMINED is grey, never green. "De-energised" is the sentence that makes
 * someone reach into a cubicle; we only say it when the data supports it
 * (AGENTS.md I2).
 *
 * Labels are not here. They are read by people, so they live in `src/i18n/`:
 * `t('state.CLOSED')`, `t('liveState.LIVE')`, `t('reason.' + code)`.
 */
export const STATE_COLOR: Record<SwitchState, string> = {
  CLOSED: 'var(--color-st-closed)',
  OPEN: 'var(--color-st-open)',
  INTERMEDIATE: 'var(--color-st-intermediate)',
  UNDETERMINED: 'var(--color-st-undetermined)',
}

export function stateColor(state: SwitchState): string {
  return STATE_COLOR[state] ?? 'var(--color-st-undetermined)'
}

/** Anything not GOOD is drawn dashed, so degraded data is visible at a glance. */
export function isDegraded(quality: Quality): boolean {
  return quality !== 'GOOD'
}

/**
 * Conductor colour from a raw IsLive reading.
 *
 * `null`/`undefined` means we do not know, and neither does the backend —
 * grey, never green (AGENTS.md I2).
 */
export function railColor(isLive: boolean | null | undefined, quality: Quality): string {
  if (quality !== 'GOOD' || isLive == null) return 'var(--color-st-undetermined)'
  return isLive ? 'var(--color-st-live)' : 'var(--color-st-dead)'
}

/**
 * Conductor colour from the backend's energisation verdict.
 *
 * UNKNOWN is grey and must stay grey. It is what the solver says when a switch
 * position is unreadable or a measurement is missing, and the whole point of
 * having that state is that it does not quietly become green.
 */
export const LIVE_COLOR: Record<LiveState, string> = {
  LIVE: 'var(--color-st-live)',
  DEAD: 'var(--color-st-dead)',
  EARTHED: 'var(--color-st-earthed)',
  UNKNOWN: 'var(--color-st-undetermined)',
}

export function liveColor(state: LiveState): string {
  return LIVE_COLOR[state] ?? 'var(--color-st-undetermined)'
}
