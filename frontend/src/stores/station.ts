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
import {
  ApiError,
  api,
  type Bay,
  type Energization,
  type LiveState,
  type Station,
  type StationDiagram,
} from '@/api/client'

export const useStationStore = defineStore('station', () => {
  const station = ref<Station | null>(null)
  const bays = ref<Bay[]>([])
  /** One drawing for the whole station — every voltage level, stacked. */
  const diagram = ref<StationDiagram | null>(null)
  /** Which level the side panel is describing. The drawing always shows all. */
  const voltageLevel = ref<string | null>(null)
  /** Live/dead verdict per connectivity node, solved in the backend. */
  const energization = ref<Energization | null>(null)

  const loading = ref(false)
  const reloading = ref(false)
  const error = ref<ApiError | null>(null)

  /** Verdict for one conductor. UNKNOWN when the backend did not say — the
   *  frontend never fills a gap with a guess (AGENTS.md I2, I4). */
  function liveStateOf(nodeId: string | null | undefined): LiveState {
    if (!nodeId) return 'UNKNOWN'
    return energization.value?.node_state[nodeId] ?? 'UNKNOWN'
  }

  const mismatchCount = computed(() => energization.value?.summary.mismatched ?? 0)
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
      const [summary, bayList, drawing, live] = await Promise.all([
        api.station(),
        api.bays(),
        api.stationDiagram(),
        api.energization(),
      ])
      station.value = summary
      bays.value = bayList
      diagram.value = drawing
      energization.value = live
      const wanted =
        voltageLevel.value && summary.voltage_levels.includes(voltageLevel.value)
          ? voltageLevel.value
          : summary.voltage_levels[0]
      if (wanted) selectVoltageLevel(wanted)
    } catch (cause) {
      capture(cause)
      if (cause instanceof ApiError && cause.code === 'model_not_loaded') {
        // No model server-side (e.g. the active project was deleted). Showing
        // a stale drawing next to that error would be worse than showing none.
        station.value = null
        bays.value = []
        diagram.value = null
        energization.value = null
      }
    } finally {
      loading.value = false
    }
  }

  /** Changes what the side panel lists. The drawing is not refetched. */
  function selectVoltageLevel(level: string): void {
    voltageLevel.value = level
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
    energization,
    voltageLevel,
    loading,
    reloading,
    error,
    voltageLevels,
    issues,
    errorCount,
    mismatchCount,
    baysHere,
    liveStateOf,
    load,
    selectVoltageLevel,
    reload,
  }
})
