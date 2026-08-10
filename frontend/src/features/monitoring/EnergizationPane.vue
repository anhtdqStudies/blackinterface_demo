<script setup lang="ts">
/**
 * What is live, dead, or earthed — station-wide, not narrowed to pane scope.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LiveState } from '@/api/client'
import { LIVE_COLOR } from '@/components/diagram/state'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import Empty from '@/ui/Empty.vue'
import Panel from '@/ui/Panel.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'

const { t } = useI18n()
const live = useLiveStore()
const structure = useStructureStore()

const ORDER: LiveState[] = ['LIVE', 'DEAD', 'EARTHED', 'UNKNOWN']

const energization = computed(() => live.energization)

const pending = computed(
  () => Boolean(structure.station) && !energization.value && !structure.loading,
)

const counts = computed(() => {
  const summary = energization.value?.summary
  if (!summary) return []
  const keys = {
    LIVE: summary.live,
    DEAD: summary.dead,
    EARTHED: summary.earthed,
    UNKNOWN: summary.unknown,
  }
  return ORDER.map((state) => ({
    state,
    color: LIVE_COLOR[state],
    count: keys[state] ?? 0,
  })).filter((row) => row.count > 0)
})

const compared = computed(() => energization.value?.summary.compared ?? 0)
const mismatched = computed(() => energization.value?.summary.mismatched ?? 0)

const notable = computed(
  () =>
    energization.value?.islands
      .filter((island) => island.state === 'UNKNOWN' || island.state === 'EARTHED')
      .slice(0, 8) ?? [],
)

function where(island: NonNullable<typeof energization.value>['islands'][number]): string {
  return island.busbar_ids.join(', ') || island.bay_ids.join(', ') || island.id
}
</script>

<template>
  <div class="p-3">
    <PaneSkeleton v-if="pending" variant="row" :count="4" />
    <template v-else-if="energization">
      <Panel :title="t('energization.title')">
        <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-dim">
          <span v-for="row in counts" :key="row.state">
            <i
              class="mr-[5px] inline-block h-[9px] w-[9px] rounded-[2px]"
              :style="{ background: row.color }"
              aria-hidden="true"
            />
            {{ t(`liveState.${row.state}`) }}
            <b class="text-fg">{{ row.count }}</b>
          </span>
        </div>

        <p v-if="compared === 0" class="mt-2 text-xs leading-relaxed text-dim">
          {{ t('energization.noComparison') }}
        </p>
        <p v-else-if="mismatched === 0" class="mt-2 text-xs leading-relaxed text-st-open">
          {{ t('energization.agrees', { n: compared, total: compared }) }}
        </p>
        <p v-else class="mt-2 text-xs leading-relaxed text-st-closed">
          {{ t('energization.mismatch', { n: mismatched, total: compared }) }}
        </p>
      </Panel>

      <Panel v-if="notable.length" :title="t('energization.notable')">
        <div
          v-for="island in notable"
          :key="island.id"
          class="mb-1 flex justify-between gap-2 rounded-[var(--radius)] border border-line px-2 py-1 text-sm last:mb-0"
        >
          <span>
            {{ where(island) }}
            <small class="mt-0.5 block text-dim">{{ t(`reason.${island.reason}`) }}</small>
          </span>
          <span class="text-2xs whitespace-nowrap" :style="{ color: LIVE_COLOR[island.state] }">
            {{ t(`liveState.${island.state}`) }}
          </span>
        </div>
      </Panel>
    </template>
    <Empty v-else :reason="t('pane.noEnergization')" />
  </div>
</template>
