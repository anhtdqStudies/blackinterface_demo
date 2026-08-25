<script setup lang="ts">
import { cn } from '@/lib/utils'
import { Skeleton as ShadcnSkeleton } from '@/ui/skeleton'

defineProps<{
  variant?: 'row' | 'block'
  count?: number
  class?: string
}>()
</script>

<template>
  <div
    :class="
      cn('flex flex-col gap-2 p-3', variant === 'block' && 'h-full min-h-[8rem]', $props.class)
    "
  >
    <ShadcnSkeleton
      v-for="i in count ?? 1"
      :key="i"
      :class="cn('h-4 w-full', variant === 'block' && 'min-h-[4rem] flex-1')"
    />
  </div>
</template>
