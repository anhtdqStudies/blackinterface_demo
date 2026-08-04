<script setup lang="ts">
/**
 * The station single-line diagram: every voltage level in one drawing.
 *
 * This component renders coordinates and nothing else. Which busbar a bay hangs
 * off, whether a conductor is energised, where a symbol goes — all decided in
 * the backend (AGENTS.md I4, I5). If something looks wrong here, the geometry is
 * wrong, not the drawing code.
 *
 * The one convention worth knowing: a filled dot means a real connection to a
 * busbar. A conductor crossing a busbar WITHOUT a dot is not connected to it.
 * That is what lets you see that `-1` goes to busbar 1 and `-2` to busbar 2,
 * even though both drops pass the same rails.
 */
import type { Edge, StationDiagram, Terminal } from '@/api/client'
import DeviceSymbol from './DeviceSymbol.vue'
import { railColor } from './state'

defineProps<{ diagram: StationDiagram; selectedDeviceId: string | null }>()
defineEmits<{ select: [deviceId: string] }>()

function points(edge: Edge): string {
  return edge.points.map((p) => `${p.x},${p.y}`).join(' ')
}

/** Terminals point away from the busbars: down normally, up in a mirrored band. */
function out(terminal: Terminal): number {
  return terminal.flipped ? -1 : 1
}

function arrowHead(terminal: Terminal): string {
  const { x, y } = terminal
  const d = out(terminal)
  const tip = y + d * 26
  return `${x},${tip} ${x - 5},${tip - d * 10} ${x + 5},${tip - d * 10}`
}
</script>

<template>
  <div class="canvas">
    <svg
      :width="diagram.width"
      :height="diagram.height"
      :viewBox="`0 0 ${diagram.width} ${diagram.height}`"
    >
      <!-- Voltage level bands, so it is obvious where one level ends. -->
      <g v-for="section in diagram.sections" :key="section.voltage_level">
        <line
          class="band"
          :x1="0"
          :y1="section.bottom"
          :x2="diagram.width"
          :y2="section.bottom"
        />
        <text class="level" :x="8" :y="(section.top + section.bottom) / 2">
          {{ section.voltage_level }}
        </text>
      </g>

      <!-- Busbars first: everything else hangs off them. -->
      <g v-for="rail in diagram.rails" :key="rail.busbar_id">
        <line
          :x1="rail.x1"
          :y1="rail.y"
          :x2="rail.x2"
          :y2="rail.y"
          :stroke="railColor(rail.is_live, rail.quality)"
          :stroke-width="rail.transfer ? 4 : 5"
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

      <!-- Junction dot = really connected. No dot = the conductor just crosses. -->
      <circle
        v-for="junction in diagram.junctions"
        :key="junction.id"
        :cx="junction.x"
        :cy="junction.y"
        r="4"
        fill="var(--line)"
      />

      <g v-for="terminal in diagram.terminals" :key="terminal.node_id">
        <!-- A transformer bay ends at a winding, not at open air. -->
        <template v-if="terminal.bay_type === 'TRANSFORMER'">
          <circle
            :cx="terminal.x"
            :cy="terminal.y + out(terminal) * 13"
            r="13"
            fill="none"
            stroke="var(--dim)"
            stroke-width="2"
          />
          <circle
            :cx="terminal.x"
            :cy="terminal.y + out(terminal) * 27"
            r="13"
            fill="none"
            stroke="var(--dim)"
            stroke-width="2"
          />
        </template>
        <template v-else>
          <line
            :x1="terminal.x"
            :y1="terminal.y"
            :x2="terminal.x"
            :y2="terminal.y + out(terminal) * 26"
            stroke="var(--line)"
            stroke-width="2"
          />
          <polygon :points="arrowHead(terminal)" fill="var(--dim)" />
        </template>
        <text
          :x="terminal.x"
          :y="terminal.y + out(terminal) * (terminal.bay_type === 'TRANSFORMER' ? 56 : 42)"
          text-anchor="middle"
        >
          {{ terminal.label }}
        </text>
      </g>

      <g v-for="column in diagram.columns" :key="column.bay_id">
        <text
          :x="column.x"
          :y="column.label_y"
          text-anchor="middle"
          fill="var(--fg)"
          class="bay"
        >
          {{ column.label }}
        </text>
        <text
          :x="column.x"
          :y="column.label_y + (column.flipped ? -15 : 15)"
          text-anchor="middle"
        >
          {{ column.bay_type }}
        </text>
        <text
          v-if="column.error_count"
          :x="column.x"
          :y="column.label_y + (column.flipped ? -30 : 30)"
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
      <span class="group">● có nối · dây cắt ngang thanh cái mà không có chấm = không nối</span>
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
svg text.bay {
  font-size: 12px;
}
svg text.level {
  font-size: 15px;
  font-weight: 600;
  fill: var(--dim);
  opacity: 0.5;
}
.band {
  stroke: var(--line);
  stroke-width: 1;
  stroke-dasharray: 2 8;
  opacity: 0.6;
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
