<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Issue } from '@/api/client'
import Empty from '@/ui/Empty.vue'
import Panel from '@/ui/Panel.vue'

defineProps<{ issues: Issue[]; empty?: string }>()

const { t } = useI18n()
</script>

<template>
  <Panel v-if="issues.length" :title="t('issues.title')">
    <div
      v-for="(issue, index) in issues"
      :key="index"
      class="mb-1.5 border-l-2 border-st-intermediate bg-panel-2 py-[5px] pr-2 pl-[9px] text-sm last:mb-0"
      :class="{
        'border-st-closed': issue.severity === 'error',
        'border-dim': issue.severity === 'info',
      }"
    >
      {{ issue.message }}
      <code class="mt-0.5 block text-2xs text-dim">
        {{ issue.code }}<template v-if="issue.subject"> · {{ issue.subject }}</template>
      </code>
    </div>
  </Panel>
  <Empty v-else :reason="empty ?? t('common.empty')" />
</template>
