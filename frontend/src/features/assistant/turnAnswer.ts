/**
 * Shared logic for rendering one turn's measured half (I3).
 *
 * Used while the turn is still streaming and after `answer` arrives — same
 * sentence, same ambiguity buttons, so the layout never swaps.
 */
import { computed, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Resolve, Summary } from '@/api/client'

function count(counts: Record<string, number> | undefined, name: string): number {
  return counts?.[name] ?? 0
}

export function useTurnStatement(summary: ComputedRef<Summary | null | undefined>) {
  const { t } = useI18n()
  return computed(() => {
    const payload = summary.value
    if (!payload) return ''
    const switches = payload.switch_states as Record<string, number> | undefined
    const nodes = payload.node_states as Record<string, number> | undefined
    const devices = Object.values(switches ?? {}).reduce((total, n) => total + n, 0)
    const closed = count(switches, 'CLOSED')
    const opened = count(switches, 'OPEN')
    return t('agent.answer.summary', {
      label: payload.label || payload.scope,
      devices,
      closed,
      opened,
      undetermined: devices - closed - opened,
      live: count(nodes, 'LIVE'),
      dead: count(nodes, 'DEAD'),
      unknown: count(nodes, 'UNKNOWN'),
      measurements: payload.measurements?.length ?? 0,
      issues: payload.issues?.length ?? 0,
    })
  })
}

export function useTurnCandidates(resolution: ComputedRef<Resolve | null | undefined>) {
  return computed(() => (resolution.value?.ambiguous ? resolution.value.candidates : []))
}
