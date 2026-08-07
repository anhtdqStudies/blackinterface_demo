/**
 * What the operator is looking at. The third lifetime (ADR-0014).
 *
 * `structure` outlives a reload, `live` is replaced every push, and this one
 * follows the person — it changes when they click, and it survives a refresh
 * because it lives in the URL.
 *
 * **The scope is the URL.** `#/ops/bay:D03` is the whole of "which bay is the
 * side panel describing"; there is no second copy of that answer in a
 * component's local ref. That was the previous shape and it is why the same
 * selection had to be cleared by hand in three places, and could not be linked
 * to or reloaded into.
 *
 * The same string is the pane key and the agent's tool argument (ADR-0010).
 * Producing it goes through `@/scope` and nowhere else (AGENTS.md I8).
 *
 * Since GD 1.5 this store also owns **which layout is on screen**. Scope and
 * layout belong together because they are the same lifetime — both follow the
 * person, both must survive F5 — but they are kept in different places on
 * purpose: the scope is in the path because it changes the answer, the preset is
 * in the query because it only changes the arrangement.
 */
import { defineStore } from 'pinia'
import { computed } from 'vue'
import { DEFAULT_PRESET, isPresetName, layoutFor, type PresetName } from '@/app/layout/presets'
import { isPinned, type Pane } from '@/app/layout/panes'
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

export const useWorkspaceStore = defineStore('workspace', () => {
  const structure = useStructureStore()

  /**
   * The current subject. Falls back to the station when the URL holds nothing —
   * but an unparseable scope is *not* widened to the station silently; the
   * router redirects it, so the address bar and the screen never disagree.
   */
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

  /** The bay a device/point scope belongs to, when the scope names one. */
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

  /**
   * Which voltage level the side panel describes. Derived, never stored: a
   * second copy would be one more thing to keep in step with the URL.
   *
   * A device or bay in scope answers it from the structure; otherwise it is the
   * first level the station has, so there is always something on screen.
   */
  const voltageLevel = computed<string | null>(() => {
    const current = scope.value
    if (current.kind === 'vl') return current.id
    const id = bayId.value
    if (id) return structure.bay(id)?.voltage_level ?? null
    return structure.voltageLevels[0] ?? null
  })

  /* --- the layout half (ADR-0014 §3, frontend-architecture.md §4) ---------- */

  /**
   * Which arrangement of panes is on screen. `#/ops/<scope>?l=<preset>`.
   *
   * An unknown name silently becomes the default instead of redirecting — see
   * `layoutFor`. Unlike a bad scope, a bad preset cannot make the screen say
   * something untrue about the station.
   */
  const preset = computed<PresetName>(() => {
    const raw = router.currentRoute.value.query.l
    return typeof raw === 'string' && isPresetName(raw) ? raw : DEFAULT_PRESET
  })

  const layout = computed(() => layoutFor(preset.value))

  /**
   * Change the arrangement without changing the subject.
   *
   * `replace`, not `push`: flipping between presets to find the one you want
   * should not fill the back button with layout changes. And the scope stays in
   * the path untouched, which is the acceptance criterion *"scope survives a
   * layout change"* holding by construction rather than by care.
   */
  function setPreset(next: PresetName): void {
    if (next === preset.value) return
    const current = router.currentRoute.value
    void router.replace({ path: current.path, query: { ...current.query, l: next } })
  }

  /**
   * What a pane is talking about: its pin if it has one, otherwise the workspace
   * scope. Panes never work this out themselves — one pane resolving it
   * differently is how a screen ends up describing two bays at once.
   */
  function scopeOf(pane: Pane): ScopeRef {
    return isPinned(pane) ? (pane.scope as ScopeRef) : scope.value
  }

  return { scope, bayId, deviceId, voltageLevel, go, up, preset, layout, setPreset, scopeOf }
})
