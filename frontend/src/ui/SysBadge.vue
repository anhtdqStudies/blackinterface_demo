<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { computed } from 'vue'
import { cn } from '@/lib/utils'

/** System-tone badge — sys palette only (ADR-0014 §2). */
const badge = cva(
  'inline-block min-w-4 rounded-full px-1.5 text-center text-2xs font-bold leading-4',
  {
    variants: {
      tone: {
        neutral: 'border border-border text-muted-foreground',
        info: 'bg-primary text-primary-foreground',
        warn: 'bg-sys-warn text-[#1a1200]',
        down: 'bg-sys-down text-[#2a0410]',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

type BadgeProps = VariantProps<typeof badge>

const props = defineProps<{ tone?: BadgeProps['tone']; class?: string; title?: string }>()

const classes = computed(() => cn(badge({ tone: props.tone }), props.class))
</script>

<template>
  <span :class="classes" :title="title"><slot /></span>
</template>
