<script setup lang="ts">
/**
 * Measured facts + interpretation for one turn — one layout for the whole
 * stream (I3). The statement appears as soon as `summary` returns; prose
 * accumulates beside it without replacing the structure.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Exchange } from '@/stores/chat'
import { parseScope } from '@/scope'
import { useMeasurementsStore } from '@/stores/measurements'
import { useWorkspaceStore } from '@/stores/workspace'
import SysBadge from '@/ui/SysBadge.vue'
import EvidenceBlock from '@/ui/EvidenceBlock.vue'
import MarkdownBody from '@/ui/MarkdownBody.vue'
import { Button } from '@/ui/button'
import { useTurnCandidates, useTurnStatement } from './turnAnswer'

const props = defineProps<{ turn: Exchange }>()

const { t } = useI18n()
const workspace = useWorkspaceStore()
const measurements = useMeasurementsStore()

const summary = computed(() => props.turn.summary ?? props.turn.answer?.summary ?? null)
const resolution = computed(
  () => props.turn.resolution ?? props.turn.answer?.resolution ?? null,
)
const evidence = computed(() =>
  props.turn.answer?.evidence?.length ? props.turn.answer.evidence : props.turn.reading,
)
const prose = computed(() => (props.turn.answer ? props.turn.answer.text : props.turn.text))
const unconfigured = computed(() => props.turn.answer?.unconfigured ?? false)
const llmError = computed(() => props.turn.answer?.llm_error ?? null)

const statement = useTurnStatement(summary)
const candidates = useTurnCandidates(resolution)

/** Where the turn is in the pipeline — replaces a blind spinner. */
const status = computed((): string | null => {
  if (!props.turn.pending) return null
  if (prose.value) return null
  if (summary.value) return t('chat.status.writing')
  const pending = props.turn.pendingTool
  if (pending?.tool === 'summary') {
    const scope = String(pending.args.scope ?? pending.args.query ?? '')
    return scope ? t('chat.status.reading', { scope }) : t('chat.status.readingGeneric')
  }
  if (pending?.tool === 'resolve') return t('chat.status.resolving')
  if (props.turn.tools.length === 0) return t('chat.status.callingModel')
  return t('chat.status.callingModel')
})

function pick(ref: string): void {
  const scope = parseScope(ref)
  if (scope) workspace.go(scope)
}

const answerScope = computed(() => {
  const raw = props.turn.answer?.scope ?? summary.value?.scope
  return typeof raw === 'string' ? parseScope(raw) : null
})

const showOpenSld = computed(() => Boolean(answerScope.value && summary.value))

const showOpenMeasurements = computed(
  () => answerScope.value && measurements.hasForPane(answerScope.value),
)

function openTab(kind: 'sld' | 'measurements'): void {
  const scope = answerScope.value
  if (scope) workspace.go(scope)
  workspace.setTab(kind)
  workspace.markTabPinnedByUser()
}
</script>

<template>
  <div class="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/40 p-3">
    <p v-if="status" class="m-0 text-xs text-muted-foreground">{{ status }}</p>

    <p v-if="unconfigured" class="m-0 text-sm leading-relaxed text-muted-foreground">
      {{ t('agent.answer.unconfigured') }}
    </p>

    <p
      v-if="statement"
      class="m-0 rounded-md bg-muted/50 px-3 py-2 text-sm leading-relaxed text-foreground"
    >
      {{ statement }}
    </p>

    <div v-if="candidates.length" class="flex flex-wrap gap-2">
      <Button
        v-for="candidate in candidates"
        :key="candidate.scope"
        variant="outline"
        size="sm"
        class="h-auto gap-2 py-1"
        @click="pick(candidate.scope)"
      >
        {{ candidate.label }}
        <SysBadge tone="neutral">{{ candidate.kind }}</SysBadge>
      </Button>
    </div>

    <div v-if="showOpenSld || showOpenMeasurements" class="flex flex-wrap gap-2">
      <Button v-if="showOpenSld" variant="outline" size="sm" @click="openTab('sld')">
        {{ t('chat.openTab.sld') }}
      </Button>
      <Button
        v-if="showOpenMeasurements"
        variant="outline"
        size="sm"
        @click="openTab('measurements')"
      >
        {{ t('chat.openTab.measurements') }}
      </Button>
    </div>

    <div v-if="prose" class="flex flex-col gap-2">
      <p class="m-0 text-2xs tracking-wider text-sys-idle uppercase">
        {{ t('chat.interpretation') }}
      </p>
      <MarkdownBody :source="prose" />
    </div>

    <p v-if="llmError" class="m-0 text-xs text-sys-warn">
      {{ t('chat.modelFailed', { error: llmError }) }}
    </p>

    <EvidenceBlock
      v-for="(record, i) in evidence"
      :key="`${record.tool}-${record.called_at}-${i}`"
      :evidence="record"
      compact
    />
  </div>
</template>
