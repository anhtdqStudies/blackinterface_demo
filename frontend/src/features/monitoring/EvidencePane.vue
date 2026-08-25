<script setup lang="ts">
/**
 * How much of what the rest of the screen says is worth trusting (ADR-0013).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { FileSearch } from 'lucide-vue-next'
import type { PaneProps } from '@/app/layout/panes'
import { formatScope } from '@/scope'
import { useSummaryStore } from '@/stores/summary'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import EvidenceBlock from '@/ui/EvidenceBlock.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const summary = useSummaryStore()

summary.follow()

const scopeLabel = computed(() => formatScope(props.scope))

function retry(): void {
  if (summary.asking) void summary.load(summary.asking)
}
</script>

<template>
  <div class="w-full space-y-4">
    <div class="rounded-lg border border-border/60 bg-muted/20 px-4 py-2.5">
      <p class="flex items-center gap-2 text-sm text-muted-foreground">
        <FileSearch class="size-4 shrink-0 text-primary" />
        {{ t('evidence.scopeLine', { scope: scopeLabel }) }}
      </p>
    </div>

    <PaneSkeleton v-if="summary.loading" variant="block" :count="3" />
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
