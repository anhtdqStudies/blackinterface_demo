<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/**
 * Loading placeholder that keeps its footprint.
 *
 * A pane that collapses while waiting teaches operators the software is
 * broken — same visual language as "the station is dead".
 */
const skeleton = cva('animate-pulse rounded-[var(--radius)] bg-panel-2', {
  variants: {
    variant: {
      text: 'h-3 w-full max-w-[32ch]',
      block: 'h-16 w-full',
      row: 'h-8 w-full',
    },
  },
  defaultVariants: { variant: 'text' },
})

type SkeletonProps = VariantProps<typeof skeleton>

const props = defineProps<{
  variant?: SkeletonProps['variant']
  /** How many repeated lines or rows to draw. */
  count?: number
  class?: string
}>()

const { t } = useI18n()

const lines = computed(() => Math.max(1, props.count ?? 1))
const classes = computed(() => cn(skeleton({ variant: props.variant }), props.class))
</script>

<template>
  <div class="flex flex-col gap-2 p-1" role="status" :aria-label="t('ui.loading')">
    <div v-for="index in lines" :key="index" :class="classes" />
  </div>
</template>
