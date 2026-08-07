/**
 * Display rules for one measured value (AGENTS.md I2, Q7).
 *
 * Lives in `ui/` because every pane that shows a number must obey the same
 * rules: quality gates the value, and a unit is printed only when verified.
 * `ValueCell.vue` is the visual form; these functions are the contract.
 */

/** Backend sentinel for "scale not measured". Matches `domain/measurement.py`. */
export const UNVERIFIED_UNIT = '?'

export function isValueReadable(quality: string, value: number | null | undefined): boolean {
  return quality === 'GOOD' && value !== null && value !== undefined
}

export function unitToShow(unit: string | undefined | null): string {
  if (!unit || unit === UNVERIFIED_UNIT) return ''
  return unit
}

export function formatMeasuredValue(
  value: number,
  quantity: string | undefined,
  locale: string,
): string {
  return value.toLocaleString(locale, {
    maximumFractionDigits: quantity === 'power_factor' ? 3 : 2,
  })
}

/** Convenience for rows shaped like `Reading`. */
export function isReadable(reading: { quality: string; value: number | null }): boolean {
  return isValueReadable(reading.quality, reading.value)
}

export function unitOf(reading: { unit: string }): string {
  return unitToShow(reading.unit)
}
