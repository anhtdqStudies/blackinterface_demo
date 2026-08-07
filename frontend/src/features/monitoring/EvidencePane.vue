<script setup lang="ts">
/**
 * How much of what the rest of the screen says is worth trusting (ADR-0013).
 */
import { useI18n } from 'vue-i18n'
import type { PaneProps } from '@/app/layout/panes'
import { useSummaryStore } from '@/stores/summary'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import EvidenceBlock from '@/ui/EvidenceBlock.vue'
import Skeleton from '@/ui/Skeleton.vue'

defineProps<PaneProps>()

const { t } = useI18n()
const summary = useSummaryStore()

summary.follow()

/**
 * Re-ask the question that failed, which is the one the store is holding — not
 * the pane's scope prop. The two are the same string today because nothing pins
 * an evidence pane yet; the day something does, retrying the prop would answer
 * about a different scope than the one whose error is on screen.
 */
function retry(): void {
  if (summary.asking) void summary.load(summary.asking)
}
</script>

<template>
  <div class="p-3">
    <Skeleton v-if="summary.loading" variant="block" :count="3" />
    <ErrorBox
      v-else-if="summary.error"
      :code="summary.error.code"
      :message="summary.error.message"
      @retry="retry"
    />
    <EvidenceBlock v-else-if="summary.summary" :evidence="summary.summary.evidence" />
    <Empty v-else :reason="t('pane.noEvidence')" />
  </div>
</template>
