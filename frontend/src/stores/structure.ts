/**
 * What the station *is*: bays, devices, busbars, geometry.
 *
 * Fetched once and replaced only on an explicit reload. Everything here changes
 * when the DataServer is browsed again — a different set of bays, a different
 * drawing — and at no other time.
 *
 * Stores are split by **lifetime, not by feature** (ADR-0014). A feature split
 * would put "the bay list" and "this bay's current positions" in the same
 * object, and then every switch operation in the substation would invalidate the
 * drawing. Splitting by lifetime is what keeps a position change costing one
 * small message and no re-layout.
 *
 * What is NOT here: derived electrical meaning. Whether a bay is energised,
 * which busbar feeds it, whether an interlock holds — all computed in the
 * backend (AGENTS.md I4). The frontend renders; it does not reason about the
 * power system.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api, type Bay, type Station, type StationDiagram } from '@/api/client'

export const useStructureStore = defineStore('structure', () => {
  const station = ref<Station | null>(null)
  const bays = ref<Bay[]>([])
  /** One drawing for the whole station — every voltage level, stacked. */
  const diagram = ref<StationDiagram | null>(null)

  const loading = ref(false)
  const reloading = ref(false)
  const error = ref<ApiError | null>(null)
  /** Bumped on every successful load, so dependants can react to a rebuild. */
  const generation = ref(0)

  const voltageLevels = computed(() => station.value?.voltage_levels ?? [])
  const issues = computed(() => station.value?.issues ?? [])
  const errorCount = computed(() => issues.value.filter((i) => i.severity === 'error').length)

  function bay(bayId: string): Bay | undefined {
    return bays.value.find((b) => b.id === bayId)
  }

  function baysAt(level: string | null): Bay[] {
    return level === null ? bays.value : bays.value.filter((b) => b.voltage_level === level)
  }

  function capture(cause: unknown): void {
    error.value = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
  }

  function forget(): void {
    // No model server-side (e.g. the active project was deleted). Showing a
    // stale drawing next to that error would be worse than showing none.
    station.value = null
    bays.value = []
    diagram.value = null
  }

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [summary, bayList, drawing] = await Promise.all([
        api.station(),
        api.bays(),
        api.stationDiagram(),
      ])
      station.value = summary
      bays.value = bayList
      diagram.value = drawing
      generation.value += 1
    } catch (cause) {
      capture(cause)
      if (cause instanceof ApiError && cause.code === 'model_not_loaded') forget()
    } finally {
      loading.value = false
    }
  }

  /** Ask the backend to re-read its source, then refetch everything. */
  async function reload(): Promise<void> {
    reloading.value = true
    try {
      await api.reload()
      await load()
    } catch (cause) {
      capture(cause)
    } finally {
      reloading.value = false
    }
  }

  return {
    station,
    bays,
    diagram,
    loading,
    reloading,
    error,
    generation,
    voltageLevels,
    issues,
    errorCount,
    bay,
    baysAt,
    load,
    reload,
  }
})
