<script setup lang="ts">
import { computed } from 'vue'

/**
 * The health of *this software's* link to the station. System palette only.
 *
 * This component exists because of a real defect it replaces. The header used
 * to paint "connection lost" in `--closed` (red) and "online" in `--open`
 * (green) — the same two colours that mean "breaker closed" and "disconnector
 * open" on the diagram three centimetres away. Red therefore meant both a
 * normal plant state and a fault in our own software.
 *
 * So: never red, never green (ADR-0014 section 2). Online is neutral, because
 * the absence of a warning is the signal and "online" is not a safety claim.
 */
export type SystemStatus = 'ok' | 'warn' | 'down' | 'idle'

const props = defineProps<{ status: SystemStatus; label: string; title?: string }>()

const tone = computed(
  () =>
    ({
      ok: 'text-sys-ok',
      warn: 'text-sys-warn',
      down: 'text-sys-down',
      idle: 'text-sys-idle',
    })[props.status],
)

const dot = computed(
  () =>
    ({
      ok: 'bg-sys-ok',
      warn: 'bg-sys-warn',
      down: 'bg-sys-down',
      idle: 'bg-sys-idle',
    })[props.status],
)
</script>

<template>
  <span
    class="inline-flex items-center gap-[6px] text-xs"
    :class="tone"
    :title="title ?? label"
  >
    <i
      class="h-2 w-2 rounded-full"
      :class="[dot, status === 'down' ? 'animate-pulse' : '']"
      aria-hidden="true"
    />
    {{ label }}
  </span>
</template>
