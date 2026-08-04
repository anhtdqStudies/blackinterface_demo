<script setup lang="ts">
import { computed } from 'vue'
import IssueList from '@/components/panels/IssueList.vue'
import { useStationStore } from '@/stores/station'

const store = useStationStore()

/**
 * Errors first. An `error` means part of the station could not be modelled and
 * an engineer has to look; a `warning` means we substituted something and said
 * so; `info` is bookkeeping.
 */
const bySeverity = computed(() => ({
  error: store.issues.filter((i) => i.severity === 'error'),
  warning: store.issues.filter((i) => i.severity === 'warning'),
  info: store.issues.filter((i) => i.severity === 'info'),
}))
</script>

<template>
  <div class="page">
    <h1>Cảnh báo dựng model</h1>
    <p class="dim">
      Những gì hệ thống không giải quyết được khi dựng model. Không có mục nào bị bỏ qua âm thầm
      — đây là invariant I7.
    </p>

    <h2>Lỗi ({{ bySeverity.error.length }})</h2>
    <IssueList :issues="bySeverity.error" empty="Không có lỗi." />

    <h2>Cảnh báo ({{ bySeverity.warning.length }})</h2>
    <IssueList :issues="bySeverity.warning" empty="Không có cảnh báo." />

    <h2>Thông tin ({{ bySeverity.info.length }})</h2>
    <IssueList :issues="bySeverity.info" empty="Không có." />
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
  overflow: auto;
  flex: 1;
  max-width: 900px;
}
h1 {
  font-size: 18px;
  margin: 0 0 6px;
}
h2 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  margin: 22px 0 7px;
  font-weight: 600;
}
</style>
