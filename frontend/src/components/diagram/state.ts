import type { LiveState, Quality, SwitchState } from '@/api/client'

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

/**
 * Conductor colour from the backend's energisation verdict.
 *
 * UNKNOWN is grey and must stay grey. It is what the solver says when a switch
 * position is unreadable or a measurement is missing, and the whole point of
 * having that state is that it does not quietly become green.
 */
export const LIVE_COLOR: Record<LiveState, string> = {
  LIVE: 'var(--live)',
  DEAD: 'var(--dead)',
  EARTHED: 'var(--earthed)',
  UNKNOWN: 'var(--undetermined)',
}

export const LIVE_LABEL: Record<LiveState, string> = {
  LIVE: 'CÓ ĐIỆN',
  DEAD: 'KHÔNG ĐIỆN',
  EARTHED: 'ĐÃ TIẾP ĐỊA',
  UNKNOWN: 'KHÔNG XÁC ĐỊNH',
}

/** Why the solver reached its verdict. Codes come from `domain.energization`. */
export const REASON_LABEL: Record<string, string> = {
  seeded_live: 'thanh cái ở đây đo được có điện',
  seeded_dead: 'thanh cái ở đây đo được không điện',
  through_transformer: 'lấy điện qua máy biến áp',
  possible_via_uncertain:
    'có thiết bị không đọc được vị trí — có thể đang nối vào vùng có điện',
  earthed: 'có dao tiếp địa đang đóng',
  no_measurement: 'thanh cái ở đây không đọc được IsLive',
  isolated: 'mọi đường tới nguồn đều đang mở',
}

export function liveColor(state: LiveState): string {
  return LIVE_COLOR[state] ?? 'var(--undetermined)'
}
