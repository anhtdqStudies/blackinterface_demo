/**
 * What the station is *reading*: power, current, voltage, frequency, tap.
 *
 * Its own store because it has its own cadence (ADR-0012). Analog values move
 * constantly and mean nothing electrically — they relabel the diagram, they
 * never recolour it. Keeping them out of `stores/live.ts` is what lets a load
 * ticking over every second leave the SLD alone.
 *
 * Display rules for individual readings live in `@/ui/valueCell` — this store
 * only holds the live document and scope lookups.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Measurement, Reading } from '@/api/client'
import { api } from '@/api/client'
import { formatScope, parentScope, parseScope, type ScopeRef } from '@/scope'

export const useMeasurementsStore = defineStore('measurements', () => {
  const measurement = ref<Measurement | null>(null)

  /** True once anything has arrived, so a panel can tell empty from pending. */
  const loaded = computed(() => measurement.value !== null)
  const measuredAt = computed(() => measurement.value?.measured_at ?? null)
  /** Non-null when this installation overrode the per-quantity deadbands. */
  const deadbandOverride = computed(() => measurement.value?.deadband_override_pct ?? null)

  /**
   * Readings for one scope, or an empty list.
   *
   * Empty means "this part of the station has no instrument transformers", not
   * "we failed to read it" — the backend omits a subject entirely rather than
   * sending it with blank values.
   */
  function of(scope: ScopeRef | string): Reading[] {
    const key = typeof scope === 'string' ? scope : formatScope(scope)
    return measurement.value?.readings[key] ?? []
  }

  function has(scope: ScopeRef | string): boolean {
    return of(scope).length > 0
  }

  /**
   * Where to look up readings for a pane scope.
   *
   * MMXU lives on the bay (`bay:D03`), not on each breaker. Clicking a symbol
   * on the SLD sets `device:D03.XCBR1` — exact lookup would always be empty.
   * Walk up the scope chain until a subject with readings is found.
   */
  function resolveScope(scope: ScopeRef | string): string {
    const ref = typeof scope === 'string' ? parseScope(scope) : scope
    if (!ref) return typeof scope === 'string' ? scope : 'station'

    let current: ScopeRef | null = ref
    while (current) {
      const key = formatScope(current)
      if (has(key)) return key
      current = parentScope(current)
    }
    return formatScope(ref)
  }

  function forPane(scope: ScopeRef | string): Reading[] {
    return of(resolveScope(scope))
  }

  function hasForPane(scope: ScopeRef | string): boolean {
    return forPane(scope).length > 0
  }

  function adopt(next: Measurement): void {
    measurement.value = next
  }

  async function load(): Promise<void> {
    try {
      adopt((await api.live()).measurement)
    } catch {
      // Silent for the same reason as `live.load()`: one cause, one message.
    }
  }

  return {
    measurement,
    loaded,
    measuredAt,
    deadbandOverride,
    of,
    has,
    resolveScope,
    forPane,
    hasForPane,
    adopt,
    load,
  }
})
