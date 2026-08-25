<script setup lang="ts">
/**
 * What is live, dead, or earthed — station-wide, not narrowed to pane scope.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Zap } from 'lucide-vue-next'
import type { LiveState } from '@/api/client'
import { LIVE_COLOR } from '@/components/diagram/state'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'
import Empty from '@/ui/Empty.vue'
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
  <div class="w-full space-y-4">
    <div class="rounded-lg border border-border/60 bg-muted/20 px-4 py-2.5">
      <p class="flex items-center gap-2 text-sm text-muted-foreground">
        <Zap class="size-4 shrink-0 text-primary" />
        {{ t('energization.scopeLine') }}
      </p>
    </div>

    <PaneSkeleton v-if="pending" variant="row" :count="4" />

    <template v-else-if="energization">
      <Card class="border-border/60 py-0 shadow-none">
        <CardHeader class="border-b border-border/60 px-4 py-3">
          <CardTitle class="text-sm font-medium">{{ t('energization.title') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-3 px-4 py-4">
          <div class="flex flex-wrap gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <span
              v-for="row in counts"
              :key="row.state"
              class="inline-flex items-center gap-1.5"
            >
              <i
                class="inline-block size-2.5 rounded-sm"
                :style="{ background: row.color }"
                aria-hidden="true"
              />
              {{ t(`liveState.${row.state}`) }}
              <span class="font-medium tabular-nums text-foreground">{{ row.count }}</span>
            </span>
          </div>

          <p v-if="compared === 0" class="text-sm leading-relaxed text-muted-foreground">
            {{ t('energization.noComparison') }}
          </p>
          <p v-else-if="mismatched === 0" class="text-sm leading-relaxed text-st-open">
            {{ t('energization.agrees', { n: compared, total: compared }) }}
          </p>
          <p v-else class="text-sm leading-relaxed text-st-closed">
            {{ t('energization.mismatch', { n: mismatched, total: compared }) }}
          </p>
        </CardContent>
      </Card>

      <Card v-if="notable.length" class="border-border/60 py-0 shadow-none">
        <CardHeader class="border-b border-border/60 px-4 py-3">
          <CardTitle class="text-sm font-medium">{{ t('energization.notable') }}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-2 px-4 py-4">
          <div
            v-for="island in notable"
            :key="island.id"
            class="flex justify-between gap-3 rounded-md border border-border/60 px-3 py-2 text-sm"
          >
            <span>
              {{ where(island) }}
              <small class="mt-0.5 block text-xs text-muted-foreground">
                {{ t(`reason.${island.reason}`) }}
              </small>
            </span>
            <span
              class="whitespace-nowrap text-xs font-medium"
              :style="{ color: LIVE_COLOR[island.state] }"
            >
              {{ t(`liveState.${island.state}`) }}
            </span>
          </div>
        </CardContent>
      </Card>
    </template>

    <Empty v-else :reason="t('pane.noEnergization')" />
  </div>
</template>
