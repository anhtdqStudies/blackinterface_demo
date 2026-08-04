import type { Quality, SwitchState } from '@/api/client'

/**
 * EVN/IEC convention: red = closed/energised, green = open/de-energised.
 *
 * UNDETERMINED is grey, never green. "De-energised" is the sentence that makes
 * someone reach into a cubicle; we only say it when the data supports it
 * (AGENTS.md I2).
 */
export const STATE_COLOR: Record<SwitchState, string> = {
  CLOSED: 'var(--closed)',
  OPEN: 'var(--open)',
  INTERMEDIATE: 'var(--intermediate)',
  UNDETERMINED: 'var(--undetermined)',
}

export const STATE_LABEL: Record<SwitchState, string> = {
  CLOSED: 'ĐÓNG',
  OPEN: 'MỞ',
  INTERMEDIATE: 'TRUNG GIAN',
  UNDETERMINED: 'KHÔNG XÁC ĐỊNH',
}

export function stateColor(state: SwitchState): string {
  return STATE_COLOR[state] ?? 'var(--undetermined)'
}

/** Anything not GOOD is drawn dashed, so degraded data is visible at a glance. */
export function isDegraded(quality: Quality): boolean {
  return quality !== 'GOOD'
}

/**
 * Conductor colour, OneATS Grid Designer convention: BLUE = energised,
 * GREEN = de-energised.
 *
 * Note this is not the same green as an open switch. In this convention green
 * means "no voltage here" on a conductor and "open" on a device — operators at
 * the station already read it that way, so we match rather than invent.
 *
 * `null`/`undefined` live state means we do not know, and neither does the
 * backend — grey, never green (AGENTS.md I2).
 */
export function railColor(isLive: boolean | null | undefined, quality: Quality): string {
  if (quality !== 'GOOD' || isLive == null) return 'var(--undetermined)'
  return isLive ? 'var(--live)' : 'var(--dead)'
}
