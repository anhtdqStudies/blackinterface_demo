/**
 * The `summary` facet: how the scope in view is doing, and what that rests on.
 *
 * One request per scope, refreshed when the station state changes — not on
 * every measurement tick. A summary is a judgement, and a judgement that
 * flickers with the third decimal of a load reading is one nobody reads.
 *
 * Follows the workspace's scope rather than taking one as a prop, because that
 * scope *is* the URL (ADR-0010): the evidence on screen is always evidence
 * about the address the operator is at.
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { ApiError, api, type Summary } from '@/api/client'
import { formatScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useWorkspaceStore } from '@/stores/workspace'

export const useSummaryStore = defineStore('summary', () => {
  const summary = ref<Summary | null>(null)
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  /** The scope the current answer is about, so a stale reply can be discarded. */
  let inFlight: string | null = null

  /**
   * The same string, readable from outside — what is on screen is about *this*.
   *
   * A retry button has to re-ask the question that failed, and only the store
   * knows which one that was: the pane holds a scope prop, but the answer it
   * displays comes from `follow()`, which tracks the workspace. Retrying the
   * prop would silently re-ask about something else the moment a pane is pinned.
   */
  const asking = ref<string | null>(null)

  async function load(scope: string): Promise<void> {
    inFlight = scope
    asking.value = scope
    loading.value = true
    error.value = null
    try {
      const next = await api.summary(scope)
      // A slower earlier request must not overwrite a newer answer — otherwise
      // the panel ends up describing a bay the operator has already left.
      if (inFlight === scope) summary.value = next
    } catch (cause) {
      if (inFlight !== scope) return
      summary.value = null
      error.value =
        cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
    } finally {
      if (inFlight === scope) loading.value = false
    }
  }

  let following = false

  /**
   * Start following the workspace.
   *
   * Idempotent because the caller is now a pane, and a pane is mounted and
   * unmounted every time somebody changes preset. Registering a second watcher
   * would mean two requests per scope change, then three — a leak that shows up
   * as load on the station's server, not as a broken screen.
   */
  function follow(): void {
    if (following) return
    following = true
    const workspace = useWorkspaceStore()
    const live = useLiveStore()
    watch(
      () => [formatScope(workspace.scope), live.state?.revision] as const,
      ([scope]) => void load(scope),
      { immediate: true },
    )
  }

  return { summary, asking, loading, error, load, follow }
})
