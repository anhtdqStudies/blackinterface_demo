<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Evidence } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'
import SysBadge from '@/ui/SysBadge.vue'

const props = defineProps<{ evidence: Evidence; compact?: boolean }>()

const { t, d } = useI18n()

const limits = computed(() => props.evidence.limits ?? [])
const coverage = computed(() => props.evidence.coverage)

const tone = computed(() => (coverage.value && coverage.value.missing.length ? 'down' : 'warn'))

/** Một record không đọc điểm nào — `resolve` là ca chuẩn. Nó KHÔNG "đầy đủ":
 * không có cảnh báo và không có dữ liệu trông giống nhau nếu cùng một nhãn, và
 * nhãn mạnh hơn là nhãn sai về phía nguy hiểm. Nó vẫn mang xuất xứ, đó là lý do
 * khối này vẫn hiện. */
const readNothing = computed(() => (coverage.value?.requested ?? 0) === 0)

function when(iso: string): string {
  const at = new Date(iso)
  return isNaN(at.getTime()) ? iso : d(at, 'time')
}
</script>

<template>
  <Card class="gap-2 py-3">
    <CardHeader class="px-3 py-0">
      <CardTitle
        class="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase"
      >
        {{ t('evidence.title') }}
        <!-- Tên tool hiện KỂ CẢ ở compact: một lượt chạy nhiều tool thì có nhiều
             khối, và hai khối cùng tiêu đề không nói được cái nào của cái gì. -->
        <span class="font-mono text-2xs normal-case">{{ evidence.tool }}</span>
        <SysBadge v-if="limits.length" :tone="tone">{{ limits.length }}</SysBadge>
        <SysBadge v-else-if="readNothing" tone="neutral">{{ t('evidence.noPoints') }}</SysBadge>
        <SysBadge v-else tone="neutral">{{ t('evidence.clean') }}</SysBadge>
      </CardTitle>
    </CardHeader>

    <CardContent class="space-y-2 px-3 text-xs">
      <ul v-if="limits.length" class="m-0 list-none space-y-1 p-0">
        <li v-for="limit in limits" :key="limit.code" class="flex gap-2">
          <span class="text-sys-warn" aria-hidden="true">•</span>
          <span>
            {{ t(`limit.${limit.code}`) }}
            <span v-if="limit.count" class="text-muted-foreground">({{ limit.count }})</span>
            <span
              v-if="limit.subjects.length && !compact"
              class="block font-mono text-2xs break-all text-muted-foreground"
            >
              {{ limit.subjects.join(', ') }}
            </span>
          </span>
        </li>
      </ul>

      <dl class="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-muted-foreground">
        <!-- «0 / 0 điểm» không phải một số đo về độ phủ, nó là chỗ trống. Badge
             trên tiêu đề đã nói rồi. -->
        <template v-if="!readNothing">
          <dt>{{ t('evidence.coverage') }}</dt>
          <dd class="m-0 text-foreground">
            {{ coverage?.resolved ?? 0 }} / {{ coverage?.requested ?? 0 }}
            {{ t('evidence.points') }}
          </dd>
        </template>

        <dt>{{ t('evidence.source') }}</dt>
        <dd class="m-0 text-foreground">
          {{ t(`sourceKind.${evidence.source.kind}`) }}
          <span v-if="evidence.model_version" class="text-muted-foreground">
            · ModelVersion {{ evidence.model_version }}
          </span>
        </dd>

        <dt>{{ t('evidence.at') }}</dt>
        <dd class="m-0 text-foreground">{{ when(evidence.called_at) }}</dd>

        <template v-if="!compact">
          <dt>{{ t('evidence.subject') }}</dt>
          <dd class="m-0 font-mono text-foreground">{{ evidence.subject }}</dd>
        </template>
      </dl>
    </CardContent>
  </Card>
</template>
