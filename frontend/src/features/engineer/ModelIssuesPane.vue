<script setup lang="ts">
/**
 * What the model builder could not resolve (invariant I7).
 *
 * Groups A and B only — group C is on the operator `anomalies` pane.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import IssueList from '@/features/shared/IssueList.vue'
import { useStructureStore } from '@/stores/structure'
import Empty from '@/ui/Empty.vue'
import Skeleton from '@/ui/Skeleton.vue'

const { t } = useI18n()
const structure = useStructureStore()

const modelIssues = computed(() =>
  structure.issues.filter((i) => i.group === 'A' || i.group === 'B'),
)
</script>

<template>
  <div class="p-3">
    <Skeleton v-if="structure.loading" variant="row" :count="4" />
    <IssueList
      v-else-if="structure.station"
      :issues="modelIssues"
      :empty="t('ops.noIssuesAllMatch')"
    />
    <Empty v-else :reason="t('pane.noModel')" />
  </div>
</template>
