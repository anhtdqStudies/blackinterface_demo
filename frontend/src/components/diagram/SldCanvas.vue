<script setup lang="ts">
import type { Diagram } from '@/api/client'
import DeviceSymbol from './DeviceSymbol.vue'
import { railColor } from './state'

defineProps<{ diagram: Diagram; selectedDeviceId: string | null }>()
defineEmits<{ select: [deviceId: string] }>()

function points(edge: Diagram['edges'][number]): string {
  return edge.points.map((p) => `${p.x},${p.y}`).join(' ')
}
</script>

<template>
  <div class="canvas">
    <svg
      :width="diagram.width"
      :height="diagram.height"
      :viewBox="`0 0 ${diagram.width} ${diagram.height}`"
    >
      <!-- Busbars first: everything else hangs off them. -->
      <g v-for="rail in diagram.rails" :key="rail.busbar_id">
        <line
          :x1="rail.x1"
          :y1="rail.y"
          :x2="rail.x2"
          :y2="rail.y"
          :stroke="railColor(rail.is_live, rail.quality)"
          stroke-width="5"
          stroke-linecap="round"
          :stroke-dasharray="rail.quality === 'GOOD' ? undefined : '6 5'"
        />
        <text
          :x="rail.x1 - 6"
          :y="rail.y + 4"
          text-anchor="end"
          :fill="railColor(rail.is_live, rail.quality)"
        >
          {{ rail.label }}
          <template v-if="rail.inferred">(suy ra)</template>
        </text>
      </g>

      <polyline
        v-for="edge in diagram.edges"
        :key="edge.id"
        :points="points(edge)"
        fill="none"
        stroke="var(--line)"
        stroke-width="2"
      />

      <g v-for="terminal in diagram.terminals" :key="terminal.node_id">
        <circle
          :cx="terminal.x"
          :cy="terminal.y"
          r="3.5"
          fill="var(--bg)"
          stroke="var(--dim)"
          stroke-width="2"
        />
        <text :x="terminal.x" :y="terminal.y + 17" text-anchor="middle">
          {{ terminal.label }}
        </text>
      </g>

      <g v-for="column in diagram.columns" :key="column.bay_id">
        <text :x="column.x" :y="column.bottom + 22" text-anchor="middle" fill="var(--fg)">
          {{ column.label }}
        </text>
        <text :x="column.x" :y="column.bottom + 37" text-anchor="middle">
          {{ column.bay_type }}
        </text>
        <text
          v-if="column.error_count"
          :x="column.x"
          :y="column.bottom + 52"
          text-anchor="middle"
          fill="var(--closed)"
        >
          {{ column.error_count }} lỗi
        </text>
      </g>

      <DeviceSymbol
        v-for="symbol in diagram.symbols"
        :key="symbol.device_id"
        :symbol="symbol"
        :selected="symbol.device_id === selectedDeviceId"
        @select="$emit('select', $event)"
      />
    </svg>

    <div class="legend">
      <span class="group">Thiết bị:</span>
      <span><i style="background: var(--closed)" />ĐÓNG</span>
      <span><i style="background: var(--open)" />MỞ</span>
      <span><i style="background: var(--intermediate)" />TRUNG GIAN</span>
      <span><i style="background: var(--undetermined)" />KHÔNG XÁC ĐỊNH</span>
      <span class="group">Thanh cái:</span>
      <span><i style="background: var(--live)" />có điện</span>
      <span><i style="background: var(--dead)" />không điện</span>
      <span class="group">▪ máy cắt · ◆ dao cách ly · ⏚ tiếp địa</span>
    </div>
  </div>
</template>

<style scoped>
.canvas {
  overflow: auto;
  padding: 12px;
  flex: 1;
}
svg {
  display: block;
}
svg text {
  font: 11px var(--mono);
  fill: var(--dim);
}
.legend {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: var(--dim);
  font-size: 11px;
  padding: 6px 2px;
}
.legend i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  margin-right: 5px;
}
.legend .group {
  color: var(--fg);
  opacity: 0.75;
}
</style>
