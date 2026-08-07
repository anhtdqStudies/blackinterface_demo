<script setup lang="ts">
import { cn } from '@/lib/utils'

/**
 * A failed load with a code the operator can quote on the phone.
 *
 * System palette only — this is about our software, not the plant (ADR-0014 §2).
 */
defineProps<{
  code: string
  message: string
  class?: string
}>()

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div
    :class="
      cn(
        'flex h-full flex-col items-center justify-center gap-3 rounded-[var(--radius)] border border-line bg-panel-2 p-4 text-center',
        $props.class,
      )
    "
    role="alert"
  >
    <p class="m-0 text-sm font-semibold text-fg">{{ $t('ui.errorTitle') }}</p>
    <p class="m-0 max-w-[42ch] text-sm text-dim">{{ message }}</p>
    <p class="m-0 font-mono text-2xs text-sys-idle">{{ code }}</p>
    <button
      type="button"
      class="rounded-[var(--radius)] border border-line bg-panel px-3 py-1 text-sm text-fg hover:border-accent"
      @click="emit('retry')"
    >
      {{ $t('ui.retry') }}
    </button>
  </div>
</template>
