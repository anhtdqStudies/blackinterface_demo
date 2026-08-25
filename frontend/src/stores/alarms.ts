/**
 * What the station is complaining about — alarms, open incidents, and history.
 *
 * Three views, three questions:
 * - alarm list: what is annunciated (with filters)
 * - incidents: what needs attention right now
 * - history: incidents the operator marked Done (local only, not OneATS ack)
 */
import { defineStore } from 'pinia'
import { computed, effectScope, ref, watch } from 'vue'
import { ApiError, api, type Alarm, type AlarmLive, type Incident } from '@/api/client'
import { formatScope } from '@/scope'
import { useWorkspaceStore } from '@/stores/workspace'

export const useAlarmsStore = defineStore('alarms', () => {
  const live = ref<AlarmLive | null>(null)

  const alarmRows = ref<readonly Alarm[]>([])
  const openIncidents = ref<readonly Incident[]>([])
  const historyIncidents = ref<readonly Incident[]>([])

  const alarmsAsked = ref(false)
  const incidentsAsked = ref(false)
  const historyAsked = ref(false)

  const alarmsLoading = ref(false)
  const incidentsLoading = ref(false)
  const historyLoading = ref(false)
  const dismissingId = ref<string | null>(null)
  const dismissError = ref<ApiError | null>(null)

  const alarmsError = ref<ApiError | null>(null)
  const incidentsError = ref<ApiError | null>(null)
  const historyError = ref<ApiError | null>(null)

  const askingAlarms = ref<string | null>(null)
  const askingIncidents = ref<string | null>(null)
  const askingHistory = ref<string | null>(null)

  let alarmsInFlight: string | null = null
  let incidentsInFlight: string | null = null
  let historyInFlight: string | null = null

  const known = computed(() => live.value?.has_snapshot === true)
  const openBadge = computed(() => openIncidents.value.length)

  function adopt(next: AlarmLive): void {
    live.value = next
  }

  async function loadAlarms(scope: string, includeStatus = false): Promise<void> {
    alarmsInFlight = scope
    askingAlarms.value = scope
    alarmsLoading.value = true
    alarmsError.value = null
    try {
      const next = await api.alarms(scope, includeStatus)
      if (alarmsInFlight === scope) {
        alarmRows.value = next.alarms
        alarmsAsked.value = true
      }
    } catch (cause) {
      if (alarmsInFlight !== scope) return
      alarmRows.value = []
      alarmsError.value =
        cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
    } finally {
      if (alarmsInFlight === scope) alarmsLoading.value = false
    }
  }

  async function loadOpenIncidents(scope: string): Promise<void> {
    incidentsInFlight = scope
    askingIncidents.value = scope
    incidentsLoading.value = true
    incidentsError.value = null
    try {
      const next = await api.incidents(scope, 'open')
      if (incidentsInFlight === scope) {
        openIncidents.value = next.incidents
        incidentsAsked.value = true
      }
    } catch (cause) {
      if (incidentsInFlight !== scope) return
      openIncidents.value = []
      incidentsError.value =
        cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
    } finally {
      if (incidentsInFlight === scope) incidentsLoading.value = false
    }
  }

  async function loadHistory(scope: string): Promise<void> {
    historyInFlight = scope
    askingHistory.value = scope
    historyLoading.value = true
    historyError.value = null
    try {
      const next = await api.incidents(scope, 'dismissed')
      if (historyInFlight === scope) {
        historyIncidents.value = next.incidents
        historyAsked.value = true
      }
    } catch (cause) {
      if (historyInFlight !== scope) return
      historyIncidents.value = []
      historyError.value =
        cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
    } finally {
      if (historyInFlight === scope) historyLoading.value = false
    }
  }

  async function dismiss(incidentId: string, scope: string): Promise<boolean> {
    dismissingId.value = incidentId
    dismissError.value = null
    try {
      await api.dismissIncident(incidentId, scope)
      await Promise.all([loadOpenIncidents(scope), loadHistory(scope)])
      return true
    } catch (cause) {
      dismissError.value =
        cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
      return false
    } finally {
      dismissingId.value = null
    }
  }

  let followingAlarms = false
  let followingIncidents = false
  const alarmScope = effectScope(true)
  const incidentScope = effectScope(true)

  function followAlarms(): void {
    if (followingAlarms) return
    followingAlarms = true
    const workspace = useWorkspaceStore()
    alarmScope.run(() => {
      watch(
        () => [formatScope(workspace.scope), live.value?.revision] as const,
        ([next]) => {
          void loadAlarms(next)
        },
        { immediate: true },
      )
    })
  }

  function followIncidents(): void {
    if (followingIncidents) return
    followingIncidents = true
    const workspace = useWorkspaceStore()
    incidentScope.run(() => {
      watch(
        () => [formatScope(workspace.scope), live.value?.revision] as const,
        ([next]) => {
          void loadOpenIncidents(next)
        },
        { immediate: true },
      )
    })
  }

  function followHistory(scope: string): void {
    void loadHistory(scope)
  }

  return {
    live,
    alarmRows,
    openIncidents,
    historyIncidents,
    alarmsAsked,
    incidentsAsked,
    historyAsked,
    alarmsLoading,
    incidentsLoading,
    historyLoading,
    dismissingId,
    dismissError,
    alarmsError,
    incidentsError,
    historyError,
    askingAlarms,
    askingIncidents,
    askingHistory,
    known,
    openBadge,
    adopt,
    loadAlarms,
    loadOpenIncidents,
    loadHistory,
    dismiss,
    followAlarms,
    followIncidents,
    followHistory,
  }
})
