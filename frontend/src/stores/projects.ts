/**
 * Projects: named DataServer connections.
 *
 * The flow this store exists for: create a project, type an opc.tcp:// address,
 * connect — and the structure store repaints from whatever that server holds.
 * Success also freezes a snapshot server-side, so reopening the project later
 * renders instantly without the DataServer running.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError, api, type Project } from '@/api/client'
import { useStreamStore } from '@/stores/stream'
import { useStructureStore } from '@/stores/structure'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const loading = ref(false)
  /** id of the project a connect/open/refresh is running against; -1 = create. */
  const busyId = ref<number | null>(null)
  const error = ref<ApiError | null>(null)
  /** Backend's verdict on the last connect attempt (ok=false keeps the row). */
  const lastLoadError = ref<string | null>(null)

  function capture(cause: unknown): void {
    error.value = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
  }

  async function fetchList(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      projects.value = await api.projects()
    } catch (cause) {
      capture(cause)
    } finally {
      loading.value = false
    }
  }

  /** Shared tail of create/open/refresh: record the outcome, repaint the SLD. */
  async function finish(ok: boolean, loadError: string | null): Promise<boolean> {
    lastLoadError.value = loadError
    await fetchList()
    if (ok) await Promise.all([useStructureStore().load(), useStreamStore().prime()])
    return ok
  }

  async function create(name: string, opcuaUrl: string): Promise<boolean> {
    busyId.value = -1
    error.value = null
    try {
      const result = await api.createProject(name, opcuaUrl)
      return await finish(result.ok, result.error ?? null)
    } catch (cause) {
      capture(cause)
      return false
    } finally {
      busyId.value = null
    }
  }

  async function open(id: number): Promise<boolean> {
    return act(id, () => api.openProject(id))
  }

  async function refresh(id: number): Promise<boolean> {
    return act(id, () => api.refreshProject(id))
  }

  async function act(
    id: number,
    call: () => Promise<{ ok: boolean; error?: string | null }>,
  ): Promise<boolean> {
    busyId.value = id
    error.value = null
    try {
      const result = await call()
      return await finish(result.ok, result.error ?? null)
    } catch (cause) {
      capture(cause)
      return false
    } finally {
      busyId.value = null
    }
  }

  async function remove(id: number): Promise<void> {
    busyId.value = id
    error.value = null
    try {
      projects.value = await api.deleteProject(id)
      // Deleting the active project unloads the model server-side; mirror that.
      await Promise.all([useStructureStore().load(), useStreamStore().prime()])
    } catch (cause) {
      capture(cause)
    } finally {
      busyId.value = null
    }
  }

  return {
    projects,
    loading,
    busyId,
    error,
    lastLoadError,
    fetchList,
    create,
    open,
    refresh,
    remove,
  }
})
