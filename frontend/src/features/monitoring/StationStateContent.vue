<script setup lang="ts">
/**
 * Station-wide switch positions — browse bays, drill into one (ADR-0018).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronRight, LayoutGrid, Map as MapIcon } from 'lucide-vue-next'
import type { Bay } from '@/api/client'
import { bay as bayScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'

const props = defineProps<{ voltageFilter?: string | null }>()

const { t } = useI18n()
const structure = useStructureStore()
const live = useLiveStore()
const workspace = useWorkspaceStore()

const bays = computed(() => {
  const list = structure.bays
  const filter = props.voltageFilter
  return filter ? list.filter((b) => b.voltage_level === filter) : list
})

const grouped = computed(() => {
  const map = new Map<string, Bay[]>()
  for (const bay of bays.value) {
    const level = bay.voltage_level
    const group = map.get(level)
    if (group) group.push(bay)
    else map.set(level, [bay])
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }))
})

const stationMeta = computed(() => {
  const st = structure.station
  if (!st) return null
  return t('inspector.stationMeta', { bays: st.bay_count, devices: st.device_count })
})

function openSld(): void {
  workspace.setTab('sld')
  workspace.markTabPinnedByUser()
}

function openBay(id: string): void {
  workspace.go(bayScope(id))
}

function liveLabel(bay: Bay): string {
  const liveVal = live.bayIsLive(bay.id)
  if (liveVal === true) return t('bay.live')
  if (liveVal === false) return t('bay.notLive')
  return t('bay.undetermined', { quality: bay.is_live_quality })
}
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader class="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle class="flex items-center gap-2 text-base font-semibold">
          <LayoutGrid class="size-4 text-primary" />
          {{ t('state.stationOverview') }}
        </CardTitle>
        <Button variant="outline" size="sm" class="gap-1.5" @click="openSld">
          <MapIcon class="size-3.5" />
          {{ t('state.openSld') }}
        </Button>
      </CardHeader>
      <CardContent>
        <p v-if="stationMeta" class="m-0 text-sm text-muted-foreground">{{ stationMeta }}</p>
      </CardContent>
    </Card>

    <Card
      v-for="[level, levelBays] in grouped"
      :key="level"
      class="rounded-xl border-border/70 shadow-sm"
    >
      <CardHeader class="pb-3">
        <CardTitle class="text-sm font-semibold">
          {{ t('state.baysAtLevel', { level, count: levelBays.length }) }}
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-2 pt-0">
        <button
          v-for="bay in levelBays"
          :key="bay.id"
          type="button"
          class="group flex w-full items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/40 hover:bg-muted/25"
          @click="openBay(bay.id)"
        >
          <span class="min-w-0">
            <span class="font-medium text-foreground">{{ bay.id }}</span>
            <span v-if="bay.name && bay.name !== bay.id" class="text-muted-foreground">
              · {{ bay.name }}
            </span>
            <Badge variant="outline" class="ml-2 font-mono text-2xs font-normal capitalize">
              {{ bay.bay_type }}
            </Badge>
          </span>
          <span class="flex shrink-0 items-center gap-2">
            <Badge variant="secondary" class="font-normal tabular-nums">
              {{ bay.device_count }}
            </Badge>
            <span class="text-2xs text-muted-foreground">{{ liveLabel(bay) }}</span>
            <ChevronRight
              class="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
            />
          </span>
        </button>
      </CardContent>
    </Card>
  </div>
</template>
