<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { computed } from 'vue'
import { cn } from '@/lib/utils'

/**
 * A count or a short tag. System palette — a badge is chrome, so it never
 * borrows a station colour (ADR-0014 section 2).
 */
const badge = cva(
  'inline-block min-w-4 rounded-full px-[5px] text-center text-2xs font-bold leading-4',
  {
    variants: {
      tone: {
        neutral: 'border border-line text-dim',
        info: 'bg-accent text-[#08111f]',
        warn: 'bg-sys-warn text-[#1a1200]',
        down: 'bg-sys-down text-[#2a0410]',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

type BadgeProps = VariantProps<typeof badge>

const props = defineProps<{ tone?: BadgeProps['tone']; class?: string }>()

const classes = computed(() => cn(badge({ tone: props.tone }), props.class))
</script>

<template>
  <span :class="classes"><slot /></span>
</template>
