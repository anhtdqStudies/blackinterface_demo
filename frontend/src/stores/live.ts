/**
 * What the station *is*: positions, IsLive, the solved energisation.
 *
 * The `state` cadence (ADR-0012) and nothing else. Analog readings live in
 * `stores/measurements.ts`, the connection itself in `stores/stream.ts` — this
 * store holds data and never owns a socket.
 *
 * Split from `structure` by lifetime (ADR-0014). `structure_revision` is the
 * guard between the two: if the backend browsed the station again, our geometry
 * no longer matches these keys, so we refetch the structure rather than colour
 * a drawing with ids that have moved.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { DeviceLive, Link, LiveState, State } from '@/api/client'
import { api } from '@/api/client'
import { useStructureStore } from '@/stores/structure'

export const useLiveStore = defineStore('live', () => {
  const state = ref<State | null>(null)
  const link = ref<Link | null>(null)

  /** Which conductors are live, solved in the backend. Never recomputed here. */
  const energization = computed(() => state.value?.energization ?? null)
  /**
   * True when the screen is following the station rather than showing a moment
   * in its past. Anything else must be visible to the operator — a quiet
   * station and a dropped link look identical otherwise.
   */
  const following = computed(() => link.value?.realtime === true && link.value.connected)
  const mismatchCount = computed(() => energization.value?.summary.mismatched ?? 0)

  /**
   * Verdict for one conductor. UNKNOWN when the backend did not say — the
   * frontend never fills a gap with a guess (AGENTS.md I2, I4).
   */
  function liveStateOf(nodeId: string | null | undefined): LiveState {
    if (!nodeId) return 'UNKNOWN'
    return energization.value?.node_state[nodeId] ?? 'UNKNOWN'
  }

  /**
   * A device's position as of the latest push, or undefined before the first
   * document arrives. Callers fall back to what the drawing was built with.
   */
  function deviceLive(deviceId: string): DeviceLive | undefined {
    return state.value?.devices[deviceId]
  }

  function bayIsLive(bayId: string): boolean | null | undefined {
    return state.value?.bay_is_live[bayId]
  }

  /** Apply one `state` event. Refetches the drawing when geometry moved. */
  function adopt(next: State): void {
    if (state.value && next.structure_revision !== state.value.structure_revision) {
      void useStructureStore().load()
    }
    state.value = next
  }

  /** Apply one `link` event. Its own cadence: nothing about the station. */
  function adoptLink(next: Link): void {
    link.value = next
  }

  async function load(): Promise<void> {
    try {
      const live = await api.live()
      adopt(live.state)
      adoptLink(live.link)
    } catch {
      // Deliberately silent: the structure store already reports why nothing is
      // loaded, and two errors for one cause is noise, not information.
    }
  }

  return {
    state,
    link,
    energization,
    following,
    mismatchCount,
    liveStateOf,
    deviceLive,
    bayIsLive,
    adopt,
    adoptLink,
    load,
  }
})
