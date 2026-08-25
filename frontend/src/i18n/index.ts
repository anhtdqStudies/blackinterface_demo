import { createI18n } from 'vue-i18n'

import en from './en'
import vi from './vi'

/**
 * UI language. Vietnamese by default — this runs at a Vietnamese substation.
 *
 * The distinction worth holding on to (ADR-0014): **the UI language is not the
 * answer language.** These messages are chrome — labels, units, refusal codes
 * spelled out. What the agent says back is decided per conversation, in whatever
 * language the operator asked in, and never comes through this file.
 *
 * Backend strings that reach the screen are codes, not sentences
 * (`LimitCode`, `RefusalCode`, energisation `reason`). They are translated here.
 * That is why the backend refuses to write prose: it would arrive in exactly one
 * language and be wrong in the other.
 */
export const SUPPORTED = ['vi', 'en'] as const
export type Locale = (typeof SUPPORTED)[number]

export const DEFAULT_LOCALE: Locale = 'vi'

const STORAGE_KEY = 'bi.locale'

function initialLocale(): Locale {
  const saved = globalThis.localStorage?.getItem(STORAGE_KEY)
  return isLocale(saved) ? saved : DEFAULT_LOCALE
}

export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && (SUPPORTED as readonly string[]).includes(value)
}

/**
 * When a reading was taken is a fact an operator checks against the wall clock,
 * so it is shown to the second and never as "2 minutes ago" — a relative label
 * hides the difference between slightly late and stopped.
 */
const TIME = {
  time: { hour: '2-digit', minute: '2-digit', second: '2-digit' },
  full: {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  },
} as const

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: { vi, en },
  datetimeFormats: { vi: TIME, en: TIME },
})

export function setLocale(locale: Locale): void {
  i18n.global.locale.value = locale
  globalThis.localStorage?.setItem(STORAGE_KEY, locale)
  globalThis.document?.documentElement.setAttribute('lang', locale)
}
