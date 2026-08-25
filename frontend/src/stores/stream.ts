/**
 * The one connection to the backend, and the one place events are dispatched.
 *
 * ADR-0012 asks for exactly this shape: several cadences on a single
 * EventSource, applied by **one** handler that branches on the event type
 * rather than by listeners scattered through the app. Two connections would
 * mean two reconnect policies and two answers to "are we hearing the station",
 * and a station that has gone quiet already looks like a link that has died.
 *
 * Deliberately holds no data. Owning both the socket and the state is what made
 * the old store hard to reason about; here the socket is a resource and the
 * cadences are stores.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AlarmLive, Link, Measurement, State } from '@/api/client'
import { api } from '@/api/client'
import { useAlarmsStore } from '@/stores/alarms'
import { useLiveStore } from '@/stores/live'
import { useMeasurementsStore } from '@/stores/measurements'

/** SSE event names, mirroring `api/broadcast.py::Cadence`. */
const CADENCES = ['state', 'alarm', 'measurement', 'link'] as const
type Cadence = (typeof CADENCES)[number]

export const useStreamStore = defineStore('stream', () => {
  const connected = ref(false)
  let source: EventSource | null = null

  /** Apply one event. The single branch point for everything the backend pushes. */
  function apply(cadence: Cadence, raw: string): void {
    const payload: unknown = JSON.parse(raw)
    switch (cadence) {
      case 'state':
        useLiveStore().adopt(payload as State)
        return
      case 'alarm':
        useAlarmsStore().adopt(payload as AlarmLive)
        return
      case 'measurement':
        useMeasurementsStore().adopt(payload as Measurement)
        return
      case 'link':
        useLiveStore().adoptLink(payload as Link)
    }
  }

  /** One poll of everything, for the first paint and as the SSE fallback. */
  async function prime(): Promise<void> {
    try {
      const live = await api.live()
      useLiveStore().adopt(live.state)
      useLiveStore().adoptLink(live.link)
      useMeasurementsStore().adopt(live.measurement)
      useAlarmsStore().adopt(live.alarm)
    } catch {
      // The structure store already reports why nothing is loaded.
    }
  }

  /**
   * Follow the station. EventSource reconnects on its own after a drop, so
   * there is no retry logic here — but a reconnect tells us nothing about
   * whether OneATS is reachable, which is why the badge reads `link` from the
   * backend and not this connection's own state.
   */
  function connect(): void {
    if (source || typeof EventSource === 'undefined') return
    source = new EventSource('/api/stream')
    source.onopen = () => (connected.value = true)
    source.onerror = () => (connected.value = false)
    for (const cadence of CADENCES) {
      source.addEventListener(cadence, (event) => {
        apply(cadence, (event as MessageEvent<string>).data)
      })
    }
  }

  function disconnect(): void {
    source?.close()
    source = null
    connected.value = false
  }

  return { connected, prime, connect, disconnect }
})
