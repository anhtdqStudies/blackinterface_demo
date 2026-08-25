<script setup lang="ts">
/**
 * Classified alarm list for the scope in view — the annunciator table.
 *
 * Separate from the Incidents pane on purpose: a healthy station still
 * annunciates hundreds of rows, and operators need to browse and filter them
 * without mistaking that wall for "something is wrong" (ADR-0027).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bell, History, Search, SlidersHorizontal } from 'lucide-vue-next'
import type { PaneProps } from '@/app/layout/panes'
import IncidentCard from '@/features/monitoring/IncidentCard.vue'
import type { Alarm } from '@/api/client'
import { formatScope } from '@/scope'
import { useAlarmsStore } from '@/stores/alarms'
import { Alert, AlertDescription } from '@/ui/alert'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'
import DataTable, { type DataTableColumn } from '@/ui/DataTable.vue'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import { Input } from '@/ui/input'
import { Label } from '@/ui/label'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import SysBadge from '@/ui/SysBadge.vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/ui/toggle-group'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const alarms = useAlarmsStore()

const includeStatus = ref(false)
const klassFilter = ref<'all' | Alarm['klass']>('all')
const search = ref('')
const tab = ref<'active' | 'history'>('active')

const asking = computed(() => alarms.askingAlarms ?? formatScope(props.scope))

type AlarmRow = Alarm & Record<string, unknown>

const columns: DataTableColumn<AlarmRow>[] = [
  {
    id: 't_active',
    label: t('alarmList.time'),
    sortable: true,
    sortValue: (row) => row.t_active ?? '',
  },
  {
    id: 'severity',
    label: t('alarmList.severity'),
    sortable: true,
    align: 'right',
    sortValue: (row) => row.severity,
  },
  {
    id: 'klass',
    label: t('alarmList.klass'),
    sortable: true,
    sortValue: (row) => row.klass,
  },
  {
    id: 'message',
    label: t('alarmList.message'),
    sortable: true,
    sortValue: (row) => row.message,
  },
  { id: 'point', label: t('alarmList.point'), sortable: true, sortValue: (row) => row.point },
]

const filteredRows = computed(() => {
  const needle = search.value.trim().toLowerCase()
  return alarms.alarmRows.filter((row) => {
    if (klassFilter.value !== 'all' && row.klass !== klassFilter.value) return false
    if (!needle) return true
    return [row.message, row.point, row.subject, row.klass, String(row.severity)]
      .join(' ')
      .toLowerCase()
      .includes(needle)
  }) as AlarmRow[]
})

onMounted(() => {
  alarms.followAlarms()
})

watch(includeStatus, (next) => {
  const scope = alarms.askingAlarms ?? formatScope(props.scope)
  void alarms.loadAlarms(scope, next)
})

watch(tab, (next) => {
  if (next === 'history') {
    alarms.followHistory(alarms.askingAlarms ?? formatScope(props.scope))
  }
})

function retryAlarms(): void {
  if (alarms.askingAlarms) void alarms.loadAlarms(alarms.askingAlarms, includeStatus.value)
}

function retryHistory(): void {
  if (alarms.askingHistory) void alarms.loadHistory(alarms.askingHistory)
}

function klassLabel(value: Alarm['klass']): string {
  return t(`alarms.klass.${value}`)
}

function shortTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toISOString().slice(11, 23)
}

function severityTone(value: number): 'warn' | 'neutral' {
  return value >= 600 ? 'warn' : 'neutral'
}
</script>

<template>
  <!-- flex-col: tab bar on top, content full width (nested inside workspace Tabs) -->
  <Tabs v-model="tab" class="flex w-full min-w-0 flex-col gap-4">
    <div
      class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/20 px-3 py-2"
    >
      <p class="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
        <Bell class="size-4 shrink-0 text-primary" />
        <span class="truncate">{{ t('alarms.scopeLine', { scope: asking }) }}</span>
      </p>

      <TabsList class="inline-flex h-auto shrink-0 gap-1 rounded-lg bg-muted/40 p-1">
        <TabsTrigger
          value="active"
          class="gap-1.5 px-3 text-xs text-muted-foreground data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
        >
          <Bell class="size-3.5" />
          {{ t('alarmList.tabActive') }}
        </TabsTrigger>
        <TabsTrigger
          value="history"
          class="gap-1.5 px-3 text-xs text-muted-foreground data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
        >
          <History class="size-3.5" />
          {{ t('alarmList.tabHistory') }}
          <Badge
            v-if="alarms.historyIncidents.length"
            variant="secondary"
            class="h-4 min-w-4 bg-primary/15 px-1 text-2xs tabular-nums text-primary"
          >
            {{ alarms.historyIncidents.length }}
          </Badge>
        </TabsTrigger>
      </TabsList>
    </div>

    <TabsContent value="active" class="mt-0 w-full min-w-0 space-y-4">
      <Card class="w-full rounded-xl border-border/70 shadow-sm">
        <CardHeader class="flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle class="flex items-center gap-2 text-sm font-medium">
            <SlidersHorizontal class="size-4 text-muted-foreground" />
            {{ t('alarmList.filters') }}
          </CardTitle>
          <Badge variant="secondary" class="font-normal tabular-nums">
            {{ t('alarmList.rowCount', { count: filteredRows.length }) }}
          </Badge>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <div class="space-y-2">
              <Label for="alarm-search" class="text-xs text-muted-foreground">
                {{ t('alarmList.search') }}
              </Label>
              <div class="relative">
                <Search
                  class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  id="alarm-search"
                  v-model="search"
                  :placeholder="t('alarmList.searchPlaceholder')"
                  class="h-9 pl-9"
                />
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              class="shrink-0"
              :class="includeStatus ? 'border-primary bg-primary/5' : ''"
              @click="includeStatus = !includeStatus"
            >
              {{ t('alarmList.includeStatus') }}
            </Button>
          </div>

          <div class="space-y-2">
            <Label class="text-xs text-muted-foreground">{{ t('alarmList.klass') }}</Label>
            <ToggleGroup
              v-model="klassFilter"
              type="single"
              variant="outline"
              size="sm"
              class="flex flex-wrap justify-start"
            >
              <ToggleGroupItem value="all" class="text-xs">{{
                t('alarmList.all')
              }}</ToggleGroupItem>
              <ToggleGroupItem value="fault" class="text-xs">{{
                t('alarms.klass.fault')
              }}</ToggleGroupItem>
              <ToggleGroupItem value="status" class="text-xs">{{
                t('alarms.klass.status')
              }}</ToggleGroupItem>
              <ToggleGroupItem value="config" class="text-xs">{{
                t('alarms.klass.config')
              }}</ToggleGroupItem>
              <ToggleGroupItem value="unknown" class="text-xs">{{
                t('alarms.klass.unknown')
              }}</ToggleGroupItem>
            </ToggleGroup>
          </div>
        </CardContent>
      </Card>

      <PaneSkeleton
        v-if="alarms.alarmsLoading && !alarms.alarmRows.length"
        variant="row"
        :count="6"
      />

      <ErrorBox
        v-else-if="alarms.alarmsError"
        :code="alarms.alarmsError.code"
        :message="alarms.alarmsError.message"
        @retry="retryAlarms"
      />

      <DataTable
        v-else-if="filteredRows.length"
        framed
        class="w-full"
        :columns="columns"
        :rows="filteredRows"
        :row-key="(row) => row.event_id"
        default-sort-column="t_active"
        default-sort-direction="desc"
      >
        <template #cell-t_active="{ row }">
          <span class="font-mono text-xs tabular-nums text-muted-foreground">{{
            shortTime(row.t_active)
          }}</span>
        </template>
        <template #cell-severity="{ row }">
          <SysBadge :tone="severityTone(row.severity)" class="tabular-nums">
            {{ row.severity }}
          </SysBadge>
        </template>
        <template #cell-klass="{ row }">
          <SysBadge :tone="row.klass === 'fault' ? 'warn' : 'neutral'">
            {{ klassLabel(row.klass) }}
          </SysBadge>
        </template>
        <template #cell-message="{ row }">
          <span class="text-sm leading-snug">{{ row.message || '—' }}</span>
        </template>
        <template #cell-point="{ row }">
          <span class="font-mono text-2xs text-muted-foreground">{{ row.point }}</span>
        </template>
      </DataTable>

      <Empty v-else-if="!alarms.known" :reason="t('alarms.unknownYet')" />
      <Empty v-else-if="!alarms.alarmsAsked" :reason="t('alarms.notAsked')" />
      <Empty v-else :reason="t('alarmList.noneInScope', { scope: asking })" />
    </TabsContent>

    <TabsContent value="history" class="mt-0 w-full min-w-0 space-y-4">
      <Alert class="border-border/60 bg-muted/20">
        <History class="size-4 text-muted-foreground" />
        <AlertDescription class="text-sm leading-relaxed text-muted-foreground">
          {{ t('alarmList.historyHint') }}
        </AlertDescription>
      </Alert>

      <PaneSkeleton
        v-if="alarms.historyLoading && !alarms.historyIncidents.length"
        variant="row"
        :count="2"
      />

      <ErrorBox
        v-else-if="alarms.historyError"
        :code="alarms.historyError.code"
        :message="alarms.historyError.message"
        @retry="retryHistory"
      />

      <div v-else-if="alarms.historyIncidents.length" class="space-y-4">
        <IncidentCard
          v-for="incident in alarms.historyIncidents"
          :key="`${incident.id}-${incident.dismissed_at}`"
          :incident="incident"
          dismissed
        />
      </div>

      <Empty v-else-if="!alarms.historyAsked" :reason="t('alarms.notAsked')" />
      <Empty v-else :reason="t('alarmList.noHistory', { scope: asking })" />
    </TabsContent>
  </Tabs>
</template>
