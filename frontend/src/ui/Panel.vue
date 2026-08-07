<script setup lang="ts">
import { cn } from '@/lib/utils'

/**
 * A titled block in a side panel. The heading style was copy-pasted into five
 * components before this existed — same eleven pixels, same letter-spacing,
 * five places to change it.
 */
defineProps<{ title?: string; class?: string }>()
</script>

<template>
  <section :class="cn('mb-4', $props.class)">
    <h2
      v-if="title"
      class="mb-[7px] text-xs font-semibold tracking-[0.08em] text-dim uppercase"
    >
      {{ title }}
      <slot name="title-extra" />
    </h2>
    <slot />
  </section>
</template>
