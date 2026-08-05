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
 *
 * Two kinds of state, two lifetimes:
 *
 *   `station` / `bays` / `diagram`   structure and geometry — fetched once,
 *                                    replaced only on an explicit reload
 *   `live`                           everything that moves — arrives on the
 *                                    SSE stream, replaced constantly
 *
 * That split is why a switch operating in the substation costs one small
 * message and no re-layout. `live.structure_revision` is the guard on it: if
 * the backend browsed the station again, our drawing is stale and we refetch
 * rather than colour a diagram with keys that no longer match.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  ApiError,
  api,
  type Bay,
  type DeviceLive,
  type Live,
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
  /** Everything that moves: positions, IsLive, the solved energisation. */
  const live = ref<Live | null>(null)

  const loading = ref(false)
  const reloading = ref(false)
  const error = ref<ApiError | null>(null)

  /** Which conductors are live, solved in the backend. Never recomputed here. */
  const energization = computed(() => live.value?.energization ?? null)
  /** State of the subscription, not of the station. */
  const link = computed(() => live.value?.link ?? null)
  /** True when the screen is following the station rather than showing a
   *  moment in its past. Anything else must be visible to the operator. */
  const following = computed(() => link.value?.realtime === true && link.value.connected)

  /** Verdict for one conductor. UNKNOWN when the backend did not say — the
   *  frontend never fills a gap with a guess (AGENTS.md I2, I4). */
  function liveStateOf(nodeId: string | null | undefined): LiveState {
    if (!nodeId) return 'UNKNOWN'
    return energization.value?.node_state[nodeId] ?? 'UNKNOWN'
  }

  /** A device's position as of the latest push, or undefined before the first
   *  document arrives. Callers fall back to what the drawing was built with. */
  function deviceLive(deviceId: string): DeviceLive | undefined {
    return live.value?.devices[deviceId]
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

  /** Fetch structure and state together. Called on boot and after a reload. */
  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [summary, bayList, drawing, current] = await Promise.all([
        api.station(),
        api.bays(),
        api.stationDiagram(),
        api.live(),
      ])
      station.value = summary
      bays.value = bayList
      diagram.value = drawing
      live.value = current
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
        live.value = null
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

  // ------------------------------------------------------------------ stream
  let source: EventSource | null = null

  /** Follow the station. EventSource reconnects on its own after a drop, so
   *  there is no retry logic here — but a reconnect tells us nothing about
   *  whether OneATS is reachable, which is why `link` comes from the backend
   *  and not from this connection's own state. */
  function connect(): void {
    if (source || typeof EventSource === 'undefined') return
    source = new EventSource('/api/stream')
    source.addEventListener('live', (event) => {
      const next = JSON.parse((event as MessageEvent<string>).data) as Live
      // The station was browsed again under us — another tab refreshed the
      // project, say. Our geometry no longer matches these keys, so refetch
      // it before adopting them.
      if (live.value && next.structure_revision !== live.value.structure_revision) {
        void load()
        return
      }
      live.value = next
    })
  }

  function disconnect(): void {
    source?.close()
    source = null
  }

  return {
    station,
    bays,
    diagram,
    live,
    voltageLevel,
    loading,
    reloading,
    error,
    energization,
    link,
    following,
    voltageLevels,
    issues,
    errorCount,
    mismatchCount,
    baysHere,
    liveStateOf,
    deviceLive,
    load,
    selectVoltageLevel,
    reload,
    connect,
    disconnect,
  }
})
