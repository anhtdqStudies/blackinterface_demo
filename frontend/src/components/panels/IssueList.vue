<script setup lang="ts">
import type { Issue } from '@/api/client'

defineProps<{ issues: Issue[]; empty?: string }>()
</script>

<template>
  <div v-if="issues.length" class="list">
    <div v-for="(issue, i) in issues" :key="i" class="issue" :class="issue.severity">
      {{ issue.message }}
      <div>
        <code
          >{{ issue.code
          }}<template v-if="issue.subject"> · {{ issue.subject }}</template></code
        >
      </div>
    </div>
  </div>
  <p v-else class="empty">{{ empty ?? 'Không có.' }}</p>
</template>

<style scoped>
.issue {
  border-left: 2px solid var(--intermediate);
  padding: 5px 9px;
  margin-bottom: 6px;
  background: var(--panel-2);
  border-radius: 0 var(--radius) var(--radius) 0;
  font-size: 12px;
}
.issue.error {
  border-left-color: var(--closed);
}
.issue.info {
  border-left-color: var(--dim);
}
</style>
