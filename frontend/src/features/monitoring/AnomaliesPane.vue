<script setup lang="ts">
/**
 * Runtime anomalies (group C) on the operator surface (GĐ 1.5 lô 3).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'
import type { PaneProps } from '@/app/layout/panes'
import IssueList from '@/features/shared/IssueList.vue'
import { formatScope } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { Card, CardContent } from '@/ui/card'
import Empty from '@/ui/Empty.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const structure = useStructureStore()

const anomalies = computed(() => structure.issues.filter((i) => i.group === 'C'))

const ignoring = computed(() =>
  props.scope.kind === 'station' ? null : formatScope(props.scope),
)
</script>

<template>
  <div class="w-full space-y-4">
    <div class="rounded-lg border border-border/60 bg-muted/20 px-4 py-2.5">
      <p class="flex items-center gap-2 text-sm text-muted-foreground">
        <AlertTriangle class="size-4 shrink-0 text-primary" />
        <template v-if="ignoring">
          {{ t('anomalies.stationWide', { scope: ignoring }) }}
        </template>
        <template v-else>
          {{ t('anomalies.scopeLine') }}
        </template>
      </p>
    </div>

    <PaneSkeleton v-if="structure.loading" variant="row" :count="3" />

    <Card v-else-if="structure.station" class="border-border/60 py-0 shadow-none">
      <CardContent class="px-4 py-4">
        <IssueList :issues="anomalies" :empty="t('anomalies.none')" embedded />
      </CardContent>
    </Card>

    <Empty v-else :reason="t('pane.noModel')" />
  </div>
</template>
