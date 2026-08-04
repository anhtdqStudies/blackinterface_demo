/**
 * The station model as the UI sees it.
 *
 * One store holds what every view needs: the summary, the bay list, and the
 * diagram for the voltage level currently on screen. Views stay dumb.
 *
 * Note what is NOT here: derived electrical meaning. Whether a bay is
 * energised, which busbar it sits on, whether an interlock holds — all of that
 * is computed in the backend (AGENTS.md I4). The frontend renders; it does not
 * reason about the power system.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api, type Bay, type Diagram, type Station } from '@/api/client'

export const useStationStore = defineStore('station', () => {
  const station = ref<Station | null>(null)
  const bays = ref<Bay[]>([])
  const diagram = ref<Diagram | null>(null)
  const voltageLevel = ref<string | null>(null)

  const loading = ref(false)
  const reloading = ref(false)
  const error = ref<ApiError | null>(null)

  const voltageLevels = computed(() => station.value?.voltage_levels ?? [])
  const issues = computed(() => station.value?.issues ?? [])
  const errorCount = computed(() => issues.value.filter((i) => i.severity === 'error').length)
  const baysHere = computed(() =>
    bays.value.filter((b) => b.voltage_level === voltageLevel.value),
  )

  function capture(cause: unknown): void {
    error.value = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
  }

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [summary, bayList] = await Promise.all([api.station(), api.bays()])
      station.value = summary
      bays.value = bayList
      const wanted =
        voltageLevel.value && summary.voltage_levels.includes(voltageLevel.value)
          ? voltageLevel.value
          : summary.voltage_levels[0]
      if (wanted) await selectVoltageLevel(wanted)
    } catch (cause) {
      capture(cause)
    } finally {
      loading.value = false
    }
  }

  async function selectVoltageLevel(level: string): Promise<void> {
    voltageLevel.value = level
    try {
      diagram.value = await api.diagram(level)
    } catch (cause) {
      diagram.value = null
      capture(cause)
    }
  }

  /** Ask the backend to re-read its source, then refresh everything. */
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
    voltageLevel,
    loading,
    reloading,
    error,
    voltageLevels,
    issues,
    errorCount,
    baysHere,
    load,
    selectVoltageLevel,
    reload,
  }
})
