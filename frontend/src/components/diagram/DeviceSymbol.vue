<script setup lang="ts">
import { computed } from 'vue'
import type { Symbol_ } from '@/api/client'
import { isDegraded, stateColor } from './state'

const props = defineProps<{ symbol: Symbol_; selected: boolean }>()
defineEmits<{ select: [deviceId: string] }>()

const color = computed(() => stateColor(props.symbol.state))
const dash = computed(() => (isDegraded(props.symbol.quality) ? '3 3' : undefined))
const open = computed(() => props.symbol.state !== 'CLOSED')

/** Earth-switch hatching, three bars of decreasing width. */
const groundBars = [10, 6.5, 3]
</script>

<template>
  <g class="sym" :class="{ selected }" @click="$emit('select', symbol.device_id)">
    <!-- Masks the connecting line so an open switch reads as an actual gap. -->
    <rect :x="symbol.x - 15" :y="symbol.y - 15" width="30" height="30" fill="var(--bg)" />

    <template v-if="symbol.role === 'breaker'">
      <rect
        :x="symbol.x - 11"
        :y="symbol.y - 11"
        width="22"
        height="22"
        rx="2"
        :fill="symbol.state === 'CLOSED' ? color : 'var(--bg)'"
        :stroke="color"
        stroke-width="2"
        :stroke-dasharray="dash"
      />
    </template>

    <template v-else-if="symbol.role === 'earth_switch'">
      <line
        :x1="symbol.x"
        :y1="symbol.y - 10"
        :x2="open ? symbol.x + 9 : symbol.x"
        :y2="symbol.y + 4"
        :stroke="color"
        stroke-width="2.5"
        :stroke-dasharray="dash"
      />
      <line
        v-for="(w, i) in groundBars"
        :key="i"
        :x1="symbol.x - w"
        :y1="symbol.y + 7 + i * 3.5"
        :x2="symbol.x + w"
        :y2="symbol.y + 7 + i * 3.5"
        :stroke="color"
        stroke-width="1.8"
      />
    </template>

    <template v-else>
      <line
        :x1="symbol.x"
        :y1="symbol.y - 12"
        :x2="open ? symbol.x + 11 : symbol.x"
        :y2="symbol.y + 12"
        :stroke="color"
        stroke-width="2.5"
        :stroke-dasharray="dash"
      />
      <circle :cx="symbol.x" :cy="symbol.y - 12" r="2.4" :fill="color" />
      <circle :cx="symbol.x" :cy="symbol.y + 12" r="2.4" :fill="color" />
    </template>

    <text :x="symbol.x + 16" :y="symbol.y + 4">{{ symbol.label }}</text>

    <rect
      class="hit"
      :x="symbol.x - 16"
      :y="symbol.y - 16"
      width="32"
      height="32"
      rx="4"
      fill="transparent"
    />
  </g>
</template>

<style scoped>
.sym {
  cursor: pointer;
}
.sym:hover .hit {
  stroke: var(--accent);
  stroke-width: 1.5;
}
.sym.selected .hit {
  stroke: var(--accent);
  stroke-width: 2;
}
text {
  font: 11px var(--mono);
  fill: var(--dim);
}
</style>
