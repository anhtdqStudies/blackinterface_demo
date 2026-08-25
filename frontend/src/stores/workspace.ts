/**
 * What the operator is looking at. The third lifetime (ADR-0014).
 *
 * `structure` outlives a reload, `live` is replaced every push, and this one
 * follows the person — it changes when they click, and it survives a refresh
 * because it lives in the URL.
 *
 * **The scope is the URL.** `#/ops/bay:D03` is the whole of "which bay is the
 * side panel describing"; there is no second copy of that answer in a
 * component's local ref.
 *
 * Since ADR-0018 the workspace tab lives in `?tab=`; layout is fixed in
 * `OPERATOR_LAYOUT`.
 */
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { DEFAULT_TAB, isWorkspaceTab, type WorkspaceTabKind } from '@/app/layout/presets'
import { isPinned, type Pane, type PaneKind } from '@/app/layout/panes'
import { router } from '@/router'
import {
  STATION,
  formatScope,
  parentScope,
  parseScope,
  type ScopeRef,
  scopesEqual,
} from '@/scope'
import { useStructureStore } from '@/stores/structure'

const CHAT_COLLAPSED_KEY = 'bi.chat.collapsed'
const NAV_COLLAPSED_KEY = 'bi.workspace.navCollapsed'

function loadFlag(key: string): boolean {
  try {
    return localStorage.getItem(key) === '1'
  } catch {
    return false
  }
}

function saveFlag(key: string, on: boolean): void {
  try {
    localStorage.setItem(key, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const structure = useStructureStore()

  const scope = computed<ScopeRef>(() => {
    const raw = router.currentRoute.value.params.scope
    return parseScope(typeof raw === 'string' ? raw : null) ?? STATION
  })

  function go(next: ScopeRef): void {
    if (scopesEqual(next, scope.value)) return
    const current = router.currentRoute.value
    void router.push({
      name: 'ops',
      params: { scope: formatScope(next) },
      query: current.query,
    })
  }

  function up(): void {
    const parent = parentScope(scope.value)
    if (parent) go(parent)
  }

  const bayId = computed<string | null>(() => {
    const current = scope.value
    if (current.kind === 'bay') return current.id
    if (current.kind === 'device' || current.kind === 'point') {
      const parent = parentScope(current)
      return parent && parent.kind === 'bay' ? parent.id : null
    }
    return null
  })

  const deviceId = computed<string | null>(() =>
    scope.value.kind === 'device' ? scope.value.id : null,
  )

  const voltageLevel = computed<string | null>(() => {
    const current = scope.value
    if (current.kind === 'vl') return current.id
    const id = bayId.value
    if (id) return structure.bay(id)?.voltage_level ?? null
    return structure.voltageLevels[0] ?? null
  })

  /* --- workspace tab (ADR-0018) ------------------------------------------- */

  const tab = computed<WorkspaceTabKind>(() => {
    const raw = router.currentRoute.value.query.tab
    return typeof raw === 'string' && isWorkspaceTab(raw) ? raw : DEFAULT_TAB
  })

  /** User picked a tab manually — suppress auto-switch until scope changes. */
  const tabPinnedByUser = ref(false)

  function markTabPinnedByUser(): void {
    tabPinnedByUser.value = true
  }

  function setTab(next: PaneKind): void {
    if (!isWorkspaceTab(next)) return
    if (next === tab.value) return
    const current = router.currentRoute.value
    void router.replace({ path: current.path, query: { ...current.query, tab: next } })
  }

  watch(scope, () => {
    tabPinnedByUser.value = false
    detailsDismissed.value = false
  })

  watch(
    () => structure.issues.filter((i) => i.group === 'C' && i.severity === 'error').length,
    (count, prev) => {
      if (tabPinnedByUser.value) return
      if (count > 0 && count >= prev) setTab('anomalies')
    },
  )

  /* --- chat column collapse ------------------------------------------------ */

  const chatCollapsed = ref(loadFlag(CHAT_COLLAPSED_KEY))
  const navCollapsed = ref(loadFlag(NAV_COLLAPSED_KEY))
  /** User closed the SLD details rail for the current scope. */
  const detailsDismissed = ref(false)

  function toggleChatCollapsed(): void {
    chatCollapsed.value = !chatCollapsed.value
    saveFlag(CHAT_COLLAPSED_KEY, chatCollapsed.value)
  }

  function toggleNavCollapsed(): void {
    navCollapsed.value = !navCollapsed.value
    saveFlag(NAV_COLLAPSED_KEY, navCollapsed.value)
  }

  function dismissDetails(): void {
    detailsDismissed.value = true
  }

  function reopenDetails(): void {
    detailsDismissed.value = false
  }

  function scopeOf(pane: Pane): ScopeRef {
    return isPinned(pane) ? (pane.scope as ScopeRef) : scope.value
  }

  return {
    scope,
    bayId,
    deviceId,
    voltageLevel,
    go,
    up,
    tab,
    setTab,
    markTabPinnedByUser,
    chatCollapsed,
    toggleChatCollapsed,
    navCollapsed,
    toggleNavCollapsed,
    detailsDismissed,
    dismissDetails,
    reopenDetails,
    scopeOf,
  }
})
