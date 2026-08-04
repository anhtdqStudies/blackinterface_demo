<script setup lang="ts">
import { computed } from 'vue'
import type { Symbol_ } from '@/api/client'
import { isDegraded, stateColor } from './state'

/**
 * Symbols follow OneATS Grid Designer so operators do not have to relearn:
 * breaker = filled square, disconnector = filled diamond, earth switch = small
 * diamond over a ground hatch. Colour is the position (red closed, green open),
 * and the shape is filled in both states — an open device is not an empty one.
 *
 * Quality that is not GOOD draws the outline dashed, so degraded data is
 * visible without reading the panel.
 */
const props = defineProps<{ symbol: Symbol_; selected: boolean }>()
defineEmits<{ select: [deviceId: string] }>()

const color = computed(() => stateColor(props.symbol.state))
const dash = computed(() => (isDegraded(props.symbol.quality) ? '3 2' : undefined))
const isEarth = computed(() => props.symbol.role === 'earth_switch')
const isBreaker = computed(() => props.symbol.role === 'breaker')

const half = computed(() => (isEarth.value ? 7 : 10))
const diamond = computed(() => {
  const { x, y } = props.symbol
  const h = half.value
  return `${x},${y - h} ${x + h},${y} ${x},${y + h} ${x - h},${y}`
})

/** Ground hatch: three bars of decreasing width beyond an earth switch. */
const groundBars = [9, 6, 3]

/** In a mirrored band the ground points up, so earth is still away from the bay. */
const dir = computed(() => (props.symbol.flipped ? -1 : 1))

// Labels sit right of centre-mounted devices, and opposite the hatch for earth
// switches so two of them on the same node do not overlap.
const labelAnchor = computed(() => (props.symbol.role === 'earth_switch' ? 'middle' : 'start'))
const labelX = computed(() => (isEarth.value ? props.symbol.x : props.symbol.x + 15))
const labelY = computed(() =>
  isEarth.value ? props.symbol.y - dir.value * 12 : props.symbol.y + 4,
)
</script>

<template>
  <g class="sym" :class="{ selected }" @click="$emit('select', symbol.device_id)">
    <!-- Masks the conductor behind the symbol. -->
    <rect
      :x="symbol.x - 13"
      :y="symbol.y - 13"
      width="26"
      height="26"
      fill="var(--bg)"
      stroke="none"
    />

    <rect
      v-if="isBreaker"
      :x="symbol.x - 11"
      :y="symbol.y - 11"
      width="22"
      height="22"
      :fill="color"
      :stroke="color"
      stroke-width="2"
      :stroke-dasharray="dash"
    />

    <template v-else>
      <polygon
        :points="diamond"
        :fill="color"
        :stroke="color"
        stroke-width="2"
        :stroke-dasharray="dash"
      />
      <template v-if="isEarth">
        <line
          :x1="symbol.x"
          :y1="symbol.y + dir * half"
          :x2="symbol.x"
          :y2="symbol.y + dir * (half + 4)"
          :stroke="color"
          stroke-width="1.6"
        />
        <line
          v-for="(w, i) in groundBars"
          :key="i"
          :x1="symbol.x - w"
          :y1="symbol.y + dir * (half + 4 + i * 3)"
          :x2="symbol.x + w"
          :y2="symbol.y + dir * (half + 4 + i * 3)"
          :stroke="color"
          stroke-width="1.6"
        />
      </template>
    </template>

    <text :x="labelX" :y="labelY" :text-anchor="labelAnchor">{{ symbol.label }}</text>

    <rect
      class="hit"
      :x="symbol.x - 15"
      :y="symbol.y - 15"
      width="30"
      height="30"
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
  font: 10px var(--mono);
  fill: var(--dim);
}
</style>
