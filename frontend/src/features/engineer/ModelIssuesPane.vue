<script setup lang="ts">
/**
 * What the model builder could not resolve (invariant I7).
 *
 * Groups A and B only — group C is on the operator `anomalies` pane.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertCircle } from 'lucide-vue-next'
import IssueList from '@/features/shared/IssueList.vue'
import { useStructureStore } from '@/stores/structure'
import Empty from '@/ui/Empty.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/ui/card'

const { t } = useI18n()
const structure = useStructureStore()

const modelIssues = computed(() =>
  structure.issues.filter((i) => i.group === 'A' || i.group === 'B'),
)
</script>

<template>
  <PaneSkeleton v-if="structure.loading" variant="row" :count="4" />

  <Card v-else-if="structure.station" class="rounded-xl border-border/70 shadow-sm">
    <CardHeader>
      <CardTitle class="flex items-center gap-2 text-base font-semibold">
        <AlertCircle class="size-4 text-primary" />
        {{ t('issues.title') }}
      </CardTitle>
      <CardDescription>{{ t('issues.intro') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <IssueList embedded :issues="modelIssues" :empty="t('ops.noIssuesAllMatch')" />
    </CardContent>
  </Card>

  <Empty v-else :reason="t('pane.noModel')" />
</template>
