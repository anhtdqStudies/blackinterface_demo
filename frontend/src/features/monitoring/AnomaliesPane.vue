<script setup lang="ts">
/**
 * Runtime anomalies (group C) on the operator surface (GĐ 1.5 lô 3).
 *
 * The backend classifies issues into A/B/C; this pane shows only C — things
 * that matter while the station is running, not while the model is being built.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import IssueList from '@/features/shared/IssueList.vue'
import { useStructureStore } from '@/stores/structure'
import Empty from '@/ui/Empty.vue'
import Skeleton from '@/ui/Skeleton.vue'

const { t } = useI18n()
const structure = useStructureStore()

const anomalies = computed(() => structure.issues.filter((i) => i.group === 'C'))
</script>

<template>
  <div class="p-3">
    <Skeleton v-if="structure.loading" variant="row" :count="3" />
    <IssueList v-else-if="structure.station" :issues="anomalies" :empty="t('anomalies.none')" />
    <Empty v-else :reason="t('pane.noModel')" />
  </div>
</template>
