<script setup lang="ts">
/**
 * One incident: the alarms that belong together, and what to do about them.
 *
 * Two rules this component exists to hold.
 *
 * **It must not imply causality.** The backend groups by time and electrical
 * area; it does not claim the first alarm produced the rest. So the strongest
 * alarm is labelled "highest severity", never "cause", and a line under the
 * cluster says what the grouping does and does not mean. Causality is `trace`
 * (ADR-0024), which does not exist yet.
 *
 * **Unapproved guidance must not look approved.** Everything bundled today is
 * `draft` — composed by an agent, reviewed by nobody with authority over this
 * substation. The badge and the hint are not decoration; they are the whole
 * reason it is safe to ship guidance at all (ADR-0027 §3).
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Clock,
  Info,
  ListTree,
} from 'lucide-vue-next'
import type { Incident } from '@/api/client'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/ui/alert'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Card, CardContent, CardTitle } from '@/ui/card'
import { Separator } from '@/ui/separator'
import SysBadge from '@/ui/SysBadge.vue'

const props = withDefaults(
  defineProps<{
    incident: Incident
    dismissed?: boolean
    dismissing?: boolean
    /** When true, details are shown on first paint (e.g. single incident). */
    defaultExpanded?: boolean
  }>(),
  { dismissed: false, dismissing: false, defaultExpanded: false },
)

const emit = defineEmits<{ done: [] }>()

const { t } = useI18n()
const expanded = ref(props.defaultExpanded)

/** How long the whole cluster took. Measured cascades run tens of ms. */
const spanMs = computed(() => {
  const { started_at: from, ended_at: to } = props.incident
  if (!from || !to) return null
  return Math.round(new Date(to).getTime() - new Date(from).getTime())
})

const isDraft = computed(() => props.incident.playbook?.status === 'draft')

/** Severity drives emphasis only — sys tones, never the diagram palette. */
const tone = computed(() => (props.incident.severity >= 600 ? 'warn' : 'neutral'))

function shortTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toISOString().slice(11, 23)
}

function toggleExpanded(): void {
  expanded.value = !expanded.value
}

function onDoneClick(event: MouseEvent): void {
  event.stopPropagation()
  emit('done')
}
</script>

<template>
  <Card
    class="overflow-hidden rounded-xl border-border/70 shadow-sm transition-colors"
    :class="expanded ? 'border-primary/25 bg-card' : 'hover:border-border'"
  >
    <!-- Collapsed summary — always visible; click to expand -->
    <button
      type="button"
      class="flex w-full cursor-pointer items-start gap-2 border-0 bg-muted/20 px-4 py-3 text-left transition-colors hover:bg-muted/30"
      :aria-expanded="expanded"
      @click="toggleExpanded"
    >
      <SysBadge :tone="tone" class="mt-0.5 shrink-0">{{ incident.severity }}</SysBadge>

      <div class="min-w-0 flex-1">
        <CardTitle class="text-base leading-snug">
          {{ incident.seed.message || incident.seed.point }}
        </CardTitle>
        <p class="mt-0.5 font-mono text-2xs text-muted-foreground">{{ incident.subject }}</p>
        <p v-if="expanded && incident.seed.actor" class="mt-1 text-xs text-muted-foreground">
          {{ t('alarms.byOperator', { actor: incident.seed.actor }) }}
        </p>
      </div>

      <div class="flex shrink-0 items-center gap-2">
        <Badge
          v-if="dismissed && incident.dismissed_at"
          variant="secondary"
          class="font-normal"
        >
          {{ t('alarmList.dismissedAt', { time: shortTime(incident.dismissed_at) }) }}
        </Badge>
        <Badge
          v-else-if="spanMs !== null"
          variant="outline"
          class="gap-1 font-normal tabular-nums"
        >
          <Clock class="size-3" />
          {{ t('alarms.span', { ms: spanMs }) }}
        </Badge>

        <Button
          v-if="!dismissed"
          size="sm"
          variant="outline"
          class="gap-1"
          :disabled="dismissing"
          @click="onDoneClick"
        >
          <CheckCircle2 class="size-3.5" />
          {{ dismissing ? t('alarmList.dismissing') : t('alarmList.done') }}
        </Button>

        <ChevronDown
          class="size-4 shrink-0 text-muted-foreground transition-transform duration-200"
          :class="cn(expanded && 'rotate-180')"
        />
      </div>
    </button>

    <CardContent v-show="expanded" class="space-y-4 border-t border-border/50 pt-4">
      <!-- The alarms in the cluster. Faults first, then what rode along. -->
      <section>
        <h4
          class="mb-2 flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          <AlertTriangle class="size-3.5" />
          {{ t('alarms.faults') }}
        </h4>
        <ul class="overflow-hidden rounded-lg border border-border/60 bg-muted/15">
          <li
            v-for="alarm in incident.faults"
            :key="alarm.event_id"
            class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-b border-border/40 px-3 py-2.5 text-sm last:border-b-0 hover:bg-muted/25"
          >
            <span class="w-20 shrink-0 tabular-nums text-muted-foreground">{{
              shortTime(alarm.t_active)
            }}</span>
            <span class="w-10 shrink-0 tabular-nums font-medium">{{ alarm.severity }}</span>
            <span class="min-w-0 flex-1">{{ alarm.message }}</span>
            <span class="shrink-0 font-mono text-2xs text-muted-foreground">{{
              alarm.point
            }}</span>
          </li>
        </ul>
      </section>

      <section v-if="incident.evidence.length">
        <h4
          class="mb-2 flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          <ListTree class="size-3.5" />
          {{ t('alarms.evidence') }}
        </h4>
        <ul class="overflow-hidden rounded-lg border border-border/60 bg-muted/10">
          <li
            v-for="alarm in incident.evidence"
            :key="alarm.event_id"
            class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-b border-border/40 px-3 py-2 text-sm text-muted-foreground last:border-b-0"
          >
            <span class="w-20 shrink-0 tabular-nums">{{ shortTime(alarm.t_active) }}</span>
            <span class="min-w-0 flex-1">{{ alarm.message }}</span>
            <span class="shrink-0 font-mono text-2xs">{{ alarm.point }}</span>
          </li>
        </ul>
      </section>

      <p
        v-if="incident.flapping_points.length"
        class="rounded-lg border border-border/60 bg-muted/15 px-3 py-2 text-sm text-muted-foreground"
      >
        <SysBadge tone="neutral" class="mr-1.5">{{ t('alarms.flapping') }}</SysBadge>
        {{ t('alarms.flappingHint') }}
        <span class="ml-1 font-mono text-2xs">{{ incident.flapping_points.join(', ') }}</span>
      </p>

      <Alert class="border-border/60 bg-muted/20">
        <Info class="size-4 text-muted-foreground" />
        <AlertDescription class="text-xs leading-relaxed text-muted-foreground">
          {{ t('alarms.notCause') }}
        </AlertDescription>
      </Alert>

      <Separator />

      <section v-if="incident.playbook">
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <h4
            class="flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase"
          >
            <BookOpen class="size-3.5" />
            {{ t('alarms.guidance') }}
          </h4>
          <Badge v-if="isDraft" variant="outline" class="border-sys-warn/40 text-sys-warn">
            {{ t('alarms.draft') }}
          </Badge>
        </div>

        <Alert v-if="isDraft" class="mb-3 border-sys-warn/30 bg-sys-warn/5">
          <AlertTriangle class="text-sys-warn" />
          <AlertDescription class="text-xs leading-relaxed text-muted-foreground">
            {{ t('alarms.draftHint') }}
          </AlertDescription>
        </Alert>

        <p class="mb-2 text-sm font-semibold text-foreground">{{ incident.playbook.title }}</p>
        <p
          v-if="incident.playbook.summary"
          class="mb-3 text-sm leading-relaxed text-muted-foreground"
        >
          {{ incident.playbook.summary }}
        </p>

        <ol class="ml-1 space-y-3 text-sm leading-relaxed">
          <li v-for="(step, index) in incident.playbook.steps" :key="index" class="flex gap-3">
            <span
              class="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-medium text-primary"
            >
              {{ index + 1 }}
            </span>
            <div class="min-w-0 pt-0.5">
              <span>{{ step.text }}</span>
              <p
                v-if="step.caution"
                class="mt-1.5 rounded-md bg-muted/30 px-2.5 py-1.5 text-xs text-muted-foreground"
              >
                <strong class="text-foreground">{{ t('alarms.caution') }}:</strong>
                {{ step.caution }}
              </p>
            </div>
          </li>
        </ol>

        <details
          v-if="incident.playbook.references.length"
          class="mt-4 rounded-lg border border-border/60 px-3 py-2"
        >
          <summary class="cursor-pointer text-xs font-medium text-muted-foreground">
            {{ t('alarms.references') }}
          </summary>
          <ul class="mt-2 space-y-1 pl-4 text-xs text-muted-foreground">
            <li v-for="(reference, index) in incident.playbook.references" :key="index">
              {{ reference }}
            </li>
          </ul>
        </details>
      </section>

      <p v-else class="text-sm text-muted-foreground">{{ t('alarms.noGuidance') }}</p>
    </CardContent>
  </Card>
</template>
