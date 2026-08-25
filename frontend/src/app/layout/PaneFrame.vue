<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isPinned, PANE_TITLE_KEY, type Pane } from './panes'
import { formatScope, type ScopeRef } from '@/scope'
import { Card, CardHeader } from '@/ui/card'
import SysBadge from '@/ui/SysBadge.vue'

const props = defineProps<{ pane: Pane; scope: ScopeRef }>()

const { t } = useI18n()

const title = computed(() => t(PANE_TITLE_KEY[props.pane.kind]))

const pin = computed(() => (isPinned(props.pane) ? formatScope(props.scope) : null))

const minimalChrome = computed(() => props.pane.params?.chrome === 'minimal')
</script>

<template>
  <div v-if="minimalChrome" class="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
    <slot />
  </div>

  <Card
    v-else
    class="flex h-full min-h-0 min-w-0 flex-col gap-0 rounded-lg border-border py-0 shadow-none"
  >
    <CardHeader
      class="flex shrink-0 flex-row items-center gap-2 border-b border-border px-3 py-2"
    >
      <span class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        {{ title }}
      </span>
      <SysBadge v-if="pin" tone="warn" :title="t('pane.pinnedHint')">
        {{ t('pane.pinned', { scope: pin }) }}
      </SysBadge>
    </CardHeader>

    <div class="min-h-0 flex-1 overflow-auto p-3">
      <slot />
    </div>
  </Card>
</template>
