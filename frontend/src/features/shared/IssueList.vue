<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Issue } from '@/api/client'
import Empty from '@/ui/Empty.vue'
import Panel from '@/ui/Panel.vue'
import { Alert, AlertDescription } from '@/ui/alert'

defineProps<{ issues: Issue[]; empty?: string }>()

const { t } = useI18n()
</script>

<template>
  <Panel v-if="issues.length" :title="t('issues.title')">
    <Alert
      v-for="(issue, index) in issues"
      :key="index"
      :variant="issue.severity === 'error' ? 'destructive' : 'default'"
      class="mb-2 border-l-2 py-2 last:mb-0"
      :class="{
        'border-l-st-closed': issue.severity === 'error',
        'border-l-st-intermediate': issue.severity === 'warning',
        'border-l-border': issue.severity === 'info',
      }"
    >
      <AlertDescription class="text-sm">
        {{ issue.message }}
        <code class="mt-0.5 block text-2xs text-muted-foreground">
          {{ issue.code }}<template v-if="issue.subject"> · {{ issue.subject }}</template>
        </code>
      </AlertDescription>
    </Alert>
  </Panel>
  <Empty v-else :reason="empty ?? t('common.empty')" />
</template>
