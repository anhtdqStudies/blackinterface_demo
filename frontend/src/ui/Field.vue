<script setup lang="ts">
import { cn } from '@/lib/utils'

/**
 * One label–value pair. The layout that was copy-pasted across device tables
 * and measurement lists, in one place.
 *
 * The value slot is intentional: a field can hold plain text, a `ValueCell`, or
 * a link — the label stays consistent either way.
 */
defineProps<{
  label: string
  /** When true, value aligns right (numbers, Dbpos). Default for measurement rows. */
  numeric?: boolean
  class?: string
}>()
</script>

<template>
  <div
    :class="
      cn(
        'grid items-baseline gap-x-2 py-[3px]',
        numeric !== false ? 'grid-cols-[1fr_auto]' : 'grid-cols-1 gap-y-1',
        $props.class,
      )
    "
  >
    <dt class="text-dim">{{ label }}</dt>
    <dd :class="cn('m-0', numeric !== false && 'text-right font-mono tabular-nums')">
      <slot />
    </dd>
  </div>
</template>
