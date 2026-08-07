<script setup lang="ts">
/**
 * One resizable block inside the scope inspector — card chrome, header, scroll body.
 */
import Badge from '@/ui/Badge.vue'

defineProps<{
  title: string
  badge?: number
  badgeTone?: 'warn' | 'down' | 'neutral'
}>()

const open = defineModel<boolean>('open', { default: true })

const emit = defineEmits<{ toggle: [] }>()
</script>

<template>
  <div
    class="mx-2 flex h-full min-h-0 flex-col overflow-hidden rounded-[var(--radius)] border border-line bg-bg shadow-[inset_0_1px_0_color-mix(in_srgb,var(--color-fg)_4%,transparent)]"
  >
    <button
      type="button"
      class="flex shrink-0 items-center gap-2 border-b border-line bg-panel-2 px-3 py-2 text-left text-sm text-fg hover:bg-panel"
      :aria-expanded="open"
      @click="emit('toggle')"
    >
      <span class="w-3 shrink-0 text-dim" aria-hidden="true">{{ open ? '▾' : '▸' }}</span>
      <span class="min-w-0 flex-1 font-medium">{{ title }}</span>
      <Badge v-if="badge && badge > 0" :tone="badgeTone ?? 'warn'" class="shrink-0">
        {{ badge }}
      </Badge>
    </button>

    <div v-show="open" class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
      <slot />
    </div>
  </div>
</template>

<style scoped>
:deep(.p-3) {
  padding-top: 8px;
  padding-bottom: 12px;
}
</style>
