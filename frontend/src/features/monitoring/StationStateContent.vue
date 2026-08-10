<script setup lang="ts">
/**
 * Station-wide switch positions — browse bays, drill into one (ADR-0018).
 *
 * Uses `structure.bays` (no per-bay fetch). Live positions come from `live`
 * when available, otherwise the snapshot from the last structure load.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Bay } from '@/api/client'
import { bay as bayScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Panel from '@/ui/Panel.vue'
import SysBadge from '@/ui/SysBadge.vue'

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
  <div class="flex flex-col gap-3">
    <Panel :title="t('state.stationOverview')">
      <p v-if="stationMeta" class="m-0 mb-2 text-sm text-muted-foreground">{{ stationMeta }}</p>
      <button type="button" class="text-sm text-primary hover:underline" @click="openSld">
        {{ t('state.openSld') }}
      </button>
    </Panel>

    <Panel
      v-for="[level, levelBays] in grouped"
      :key="level"
      :title="t('state.baysAtLevel', { level, count: levelBays.length })"
    >
      <button
        v-for="bay in levelBays"
        :key="bay.id"
        type="button"
        class="mb-1 flex w-full items-center justify-between gap-2 rounded-[var(--radius)] border border-line px-2 py-1.5 text-left text-sm hover:border-accent"
        @click="openBay(bay.id)"
      >
        <span>
          <b>{{ bay.id }}</b>
          <span v-if="bay.name && bay.name !== bay.id" class="text-muted-foreground">
            · {{ bay.name }}
          </span>
          <small class="ml-1 text-dim">{{ bay.bay_type }}</small>
        </span>
        <span class="flex shrink-0 items-center gap-2 text-2xs whitespace-nowrap">
          <SysBadge tone="neutral">{{ bay.device_count }}</SysBadge>
          <span class="text-muted-foreground">{{ liveLabel(bay) }}</span>
        </span>
      </button>
    </Panel>
  </div>
</template>
