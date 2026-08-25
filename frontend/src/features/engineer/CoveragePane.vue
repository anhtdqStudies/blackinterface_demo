<script setup lang="ts">
/**
 * How much of the station the model covers — engineering surface.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronRight, LayoutGrid } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { bayScope, opsPath } from '@/router'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Badge } from '@/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'

const { t } = useI18n()
const structure = useStructureStore()
const workspace = useWorkspaceStore()

function retry(): void {
  void structure.load()
}

const stats = computed(() => {
  const station = structure.station
  if (!station) return []
  const cov = station.coverage
  return [
    { label: t('coverage.devices'), value: String(cov.devices) },
    {
      label: t('coverage.positionGood'),
      value: `${cov.position_good} / ${cov.devices}`,
    },
    {
      label: t('coverage.determined'),
      value: `${cov.position_determined} / ${cov.devices}`,
    },
    { label: t('coverage.nodes'), value: String(station.node_count) },
  ]
})
</script>

<template>
  <PaneSkeleton v-if="structure.loading" variant="row" :count="5" />
  <ErrorBox
    v-else-if="structure.error"
    :code="structure.error.code"
    :message="structure.error.message"
    @retry="retry"
  />
  <div v-else-if="structure.station" class="space-y-4">
    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader>
        <CardTitle class="flex items-center gap-2 text-base font-semibold">
          <LayoutGrid class="size-4 text-primary" />
          {{ t('coverage.title') }}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div
            v-for="stat in stats"
            :key="stat.label"
            class="rounded-lg border border-border/60 bg-muted/20 px-3 py-3 text-center"
          >
            <p class="text-2xs tracking-wide text-muted-foreground uppercase">
              {{ stat.label }}
            </p>
            <p class="mt-1 text-lg font-semibold tabular-nums text-foreground">
              {{ stat.value }}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader>
        <CardTitle class="text-base font-semibold">
          {{ t('coverage.baysAt', { level: workspace.voltageLevel ?? '' }) }}
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-2">
        <RouterLink
          v-for="bay in structure.baysAt(workspace.voltageLevel)"
          :key="bay.id"
          class="group flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5 text-sm no-underline transition-colors hover:border-primary/40 hover:bg-muted/25"
          :to="opsPath(bayScope(bay.id))"
        >
          <span class="min-w-0">
            <span class="font-medium text-foreground">{{ bay.name }}</span>
            <span class="ml-2 text-2xs text-muted-foreground">
              {{ bay.template_id ?? t('coverage.noTemplate') }}
            </span>
          </span>
          <span class="flex shrink-0 items-center gap-2">
            <Badge variant="outline" class="font-mono text-2xs font-normal capitalize">
              {{ bay.bay_type }}
            </Badge>
            <ChevronRight
              class="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
            />
          </span>
        </RouterLink>
      </CardContent>
    </Card>
  </div>
  <Empty v-else :reason="t('pane.noModel')" />
</template>
