<script setup lang="ts">
/**
 * Open incidents for the scope in view — only what still needs attention.
 *
 * Dismissed incidents move to the Alarm list → History tab. This pane stays
 * empty on a healthy station (ADR-0027).
 */
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ShieldAlert } from 'lucide-vue-next'
import type { PaneProps } from '@/app/layout/panes'
import IncidentCard from '@/features/monitoring/IncidentCard.vue'
import { formatScope } from '@/scope'
import { useAlarmsStore } from '@/stores/alarms'
import { Alert, AlertDescription } from '@/ui/alert'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const alarms = useAlarmsStore()

onMounted(() => alarms.followIncidents())

const asking = computed(() => alarms.askingIncidents ?? formatScope(props.scope))

function retry(): void {
  if (alarms.askingIncidents) void alarms.loadOpenIncidents(alarms.askingIncidents)
}

async function onDone(incidentId: string): Promise<void> {
  const scope = alarms.askingIncidents ?? formatScope(props.scope)
  await alarms.dismiss(incidentId, scope)
}
</script>

<template>
  <div class="w-full space-y-3">
    <div class="rounded-lg border border-border/60 bg-muted/20 px-4 py-3">
      <p class="flex items-center gap-2 text-sm text-muted-foreground">
        <ShieldAlert class="size-4 shrink-0 text-primary" />
        {{ t('alarms.scopeLine', { scope: asking }) }}
      </p>
    </div>

    <Alert v-if="alarms.dismissError" variant="destructive">
      <AlertDescription>
        {{ alarms.dismissError.message }}
        <span class="text-2xs opacity-80"> ({{ alarms.dismissError.code }})</span>
      </AlertDescription>
    </Alert>

    <PaneSkeleton
      v-if="alarms.incidentsLoading && !alarms.openIncidents.length"
      variant="row"
      :count="2"
    />

    <ErrorBox
      v-else-if="alarms.incidentsError"
      :code="alarms.incidentsError.code"
      :message="alarms.incidentsError.message"
      @retry="retry"
    />

    <div v-else-if="alarms.openIncidents.length" class="space-y-4">
      <IncidentCard
        v-for="incident in alarms.openIncidents"
        :key="incident.id"
        :incident="incident"
        :dismissing="alarms.dismissingId === incident.id"
        @done="onDone(incident.id)"
      />
    </div>

    <Empty v-else-if="!alarms.known" :reason="t('alarms.unknownYet')" />
    <Empty v-else-if="!alarms.incidentsAsked" :reason="t('alarms.notAsked')" />
    <Empty v-else :reason="t('alarms.noneInScope', { scope: asking })" />
  </div>
</template>
