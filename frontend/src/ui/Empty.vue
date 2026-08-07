<script setup lang="ts">
import { RouterLink } from 'vue-router'

/**
 * Nothing to show — **and why**, plus what to do about it.
 *
 * The reason is the whole point. "No measurements" tells an operator nothing;
 * "a voltage level carries no measurements — pick a bay" tells them the next
 * move. That is why `reason` is required and why the caller passes a translated
 * string rather than this component inventing one.
 *
 * A pane must never be blank. Blank reads as broken, and on a station "is this
 * broken?" is a phone call.
 */
defineProps<{
  reason: string
  /** Optional next step, as an in-app route. */
  action?: { label: string; to: string }
}>()
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-2 p-4 text-center">
    <p class="m-0 max-w-[42ch] text-sm text-dim">{{ reason }}</p>
    <RouterLink v-if="action" :to="action.to" class="text-sm">{{ action.label }}</RouterLink>
  </div>
</template>
