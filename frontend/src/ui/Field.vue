<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{
  label: string
  numeric?: boolean
  class?: string
}>()
</script>

<template>
  <div
    :class="
      cn(
        'grid items-baseline gap-x-2 py-0.5',
        numeric !== false ? 'grid-cols-[1fr_auto]' : 'grid-cols-1 gap-y-1',
        $props.class,
      )
    "
  >
    <dt class="text-muted-foreground">{{ label }}</dt>
    <dd :class="cn('m-0', numeric !== false && 'text-right font-mono tabular-nums')">
      <slot />
    </dd>
  </div>
</template>
