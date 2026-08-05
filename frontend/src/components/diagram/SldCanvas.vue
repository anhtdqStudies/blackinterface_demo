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
 *
 * The view is a camera over that drawing: wheel zooms about the cursor, drag
 * pans, «Vừa màn hình» resets. Zooming only changes the viewBox — geometry
 * still comes from the backend untouched.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { DeviceLive, Edge, LiveState, StationDiagram } from '@/api/client'
import DeviceSymbol from './DeviceSymbol.vue'
import { liveColor } from './state'

const props = defineProps<{
  diagram: StationDiagram
  /** Live/dead verdict per connectivity node, solved in the backend. */
  nodeState: Record<string, LiveState>
  /** Latest position per device. Keyed by `SymbolView.device_id`. */
  deviceState: Record<string, DeviceLive>
  selectedDeviceId: string | null
}>()
defineEmits<{ select: [deviceId: string] }>()

function points(edge: Edge): string {
  return edge.points.map((p) => `${p.x},${p.y}`).join(' ')
}

/** Anything the backend did not rule on is UNKNOWN — grey, never green. */
function stateOf(nodeId: string | null | undefined): LiveState {
  if (!nodeId) return 'UNKNOWN'
  return props.nodeState[nodeId] ?? 'UNKNOWN'
}

function conductor(nodeId: string | null | undefined): string {
  return liveColor(stateOf(nodeId))
}

// ------------------------------------------------------------------- camera
const PAD = 40
const svgEl = ref<SVGSVGElement | null>(null)
const viewBox = ref({ x: -PAD, y: -PAD, w: 100, h: 100 })

function fit(): void {
  viewBox.value = {
    x: -PAD,
    y: -PAD,
    w: props.diagram.width + PAD * 2,
    h: props.diagram.height + PAD * 2,
  }
}
watch(() => props.diagram, fit, { immediate: true })

/** Zoom the camera onto one voltage-level band. Called by the parent's tabs. */
function focusSection(top: number, bottom: number): void {
  viewBox.value = {
    x: -PAD,
    y: top - PAD,
    w: props.diagram.width + PAD * 2,
    h: bottom - top + PAD * 2,
  }
}
defineExpose({ focusSection, fit })

/** Client pixel -> drawing coordinates, honouring the letterboxing of `meet`. */
function toDrawing(clientX: number, clientY: number): { x: number; y: number; scale: number } {
  const rect = svgEl.value!.getBoundingClientRect()
  const vb = viewBox.value
  const scale = Math.min(rect.width / vb.w, rect.height / vb.h)
  const offX = (rect.width - vb.w * scale) / 2
  const offY = (rect.height - vb.h * scale) / 2
  return {
    x: vb.x + (clientX - rect.left - offX) / scale,
    y: vb.y + (clientY - rect.top - offY) / scale,
    scale,
  }
}

function onWheel(event: WheelEvent): void {
  event.preventDefault()
  const factor = event.deltaY > 0 ? 1.2 : 1 / 1.2
  const vb = viewBox.value
  const at = toDrawing(event.clientX, event.clientY)
  viewBox.value = {
    x: at.x - (at.x - vb.x) * factor,
    y: at.y - (at.y - vb.y) * factor,
    w: vb.w * factor,
    h: vb.h * factor,
  }
}

let panning = false
let moved = false
let lastClient = { x: 0, y: 0 }

function onPointerDown(event: PointerEvent): void {
  panning = true
  moved = false
  lastClient = { x: event.clientX, y: event.clientY }
  svgEl.value?.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent): void {
  if (!panning) return
  const dx = event.clientX - lastClient.x
  const dy = event.clientY - lastClient.y
  if (Math.abs(dx) + Math.abs(dy) > 3) moved = true
  const { scale } = toDrawing(event.clientX, event.clientY)
  viewBox.value = {
    ...viewBox.value,
    x: viewBox.value.x - dx / scale,
    y: viewBox.value.y - dy / scale,
  }
  lastClient = { x: event.clientX, y: event.clientY }
}

function onPointerUp(): void {
  panning = false
}

/** A drag that ended on a symbol must not count as a click on it. */
function swallowDragClick(event: MouseEvent): void {
  if (moved) {
    event.stopPropagation()
    moved = false
  }
}

function onKey(event: KeyboardEvent): void {
  if (event.key === 'f' && !(event.target instanceof HTMLInputElement)) fit()
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="canvas">
    <svg
      ref="svgEl"
      :viewBox="`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`"
      preserveAspectRatio="xMidYMid meet"
      @wheel="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @click.capture="swallowDragClick"
    >
      <!-- Voltage level bands, so it is obvious where one level ends. -->
      <g v-for="section in diagram.sections" :key="section.voltage_level">
        <text class="level" :x="8" :y="(section.top + section.bottom) / 2">
          {{ section.voltage_level }}
        </text>
      </g>

      <!-- Busbars first: everything else hangs off them. Colour is the solved
           energisation of the conductor, not the raw IsLive point: a busbar
           whose own measurement is broken can still be known live through a
           closed coupler, and one that reads live must never be drawn dead. -->
      <g v-for="rail in diagram.rails" :key="rail.busbar_id">
        <line
          :x1="rail.x1"
          :y1="rail.y"
          :x2="rail.x2"
          :y2="rail.y"
          :stroke="conductor(rail.node_id)"
          :stroke-width="rail.transfer ? 4 : 5"
          stroke-linecap="round"
          :stroke-dasharray="stateOf(rail.node_id) === 'UNKNOWN' ? '6 5' : undefined"
        />
        <text
          :x="rail.x1 - 6"
          :y="rail.y + 4"
          text-anchor="end"
          :fill="conductor(rail.node_id)"
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
        :stroke="conductor(edge.node_id)"
        :stroke-dasharray="stateOf(edge.node_id) === 'UNKNOWN' ? '6 5' : undefined"
        stroke-width="2"
      />

      <!-- Junction dot = really connected. No dot = the conductor just crosses. -->
      <circle
        v-for="junction in diagram.junctions"
        :key="junction.id"
        :cx="junction.x"
        :cy="junction.y"
        r="4"
        :fill="conductor(junction.node_id)"
      />

      <!-- Power transformers coupling bands. Only drawn when the pairing is
           evidence-backed (BAY/Name or EVN breaker numbering), never guessed.
           A third winding (autotransformer tertiary) adds a bottom circle;
           its centre/radius must agree with TX_TAP in the backend layout. -->
      <g v-for="tx in diagram.transformers" :key="tx.id">
        <circle
          :cx="tx.x - 9"
          :cy="tx.y"
          r="16"
          fill="var(--bg)"
          stroke="var(--fg)"
          stroke-width="2.5"
        />
        <circle
          :cx="tx.x + 9"
          :cy="tx.y"
          r="16"
          fill="none"
          stroke="var(--fg)"
          stroke-width="2.5"
        />
        <circle
          v-if="tx.bay_ids.length > 2"
          :cx="tx.x"
          :cy="tx.y + 14"
          r="16"
          fill="none"
          stroke="var(--fg)"
          stroke-width="2.5"
        />
        <text
          :x="tx.x"
          :y="tx.y + (tx.bay_ids.length > 2 ? 52 : 36)"
          text-anchor="middle"
          class="tx"
        >
          {{ tx.name }}
        </text>
      </g>

      <g v-for="terminal in diagram.terminals" :key="terminal.node_id">
        <!-- A linked transformer bay continues into the drawn transformer;
             an unpaired one still ends at its own winding symbol. -->
        <template v-if="terminal.linked" />
        <template v-else-if="terminal.bay_type === 'TRANSFORMER'">
          <circle
            :cx="terminal.x"
            :cy="terminal.y + (terminal.flipped ? -13 : 13)"
            r="13"
            fill="none"
            stroke="var(--dim)"
            stroke-width="2"
          />
          <circle
            :cx="terminal.x"
            :cy="terminal.y + (terminal.flipped ? -27 : 27)"
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
            :y2="terminal.y + (terminal.flipped ? -26 : 26)"
            :stroke="conductor(terminal.node_id)"
            stroke-width="2"
          />
          <polygon
            :points="`${terminal.x},${terminal.y + (terminal.flipped ? -26 : 26)} ${terminal.x - 5},${terminal.y + (terminal.flipped ? -16 : 16)} ${terminal.x + 5},${terminal.y + (terminal.flipped ? -16 : 16)}`"
            :fill="conductor(terminal.node_id)"
          />
        </template>
      </g>

      <!-- Bay captions: designation on top, the operator's name under it. -->
      <g v-for="column in diagram.columns" :key="column.bay_id">
        <text
          :x="column.x"
          :y="column.label_y"
          text-anchor="middle"
          fill="var(--fg)"
          class="bay"
        >
          {{ column.bay_id }}
        </text>
        <text
          v-if="column.label && column.label !== column.bay_id"
          :x="column.x"
          :y="column.label_y + (column.flipped ? -15 : 15)"
          text-anchor="middle"
        >
          {{ column.label }}
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
        :live="deviceState[symbol.device_id]"
        :selected="symbol.device_id === selectedDeviceId"
        @select="$emit('select', $event)"
      />
    </svg>

    <button class="fit" title="Vừa màn hình (phím f)" @click="fit()">Vừa màn hình</button>

    <div class="legend">
      <span class="group">Thiết bị:</span>
      <span><i style="background: var(--closed)" />ĐÓNG</span>
      <span><i style="background: var(--open)" />MỞ</span>
      <span><i style="background: var(--intermediate)" />TRUNG GIAN</span>
      <span><i style="background: var(--undetermined)" />KHÔNG XÁC ĐỊNH</span>
      <span class="group">Dây dẫn:</span>
      <span><i style="background: var(--live)" />có điện</span>
      <span><i style="background: var(--dead)" />không điện</span>
      <span><i style="background: var(--earthed)" />đã tiếp địa</span>
      <span><i style="background: var(--undetermined)" />chưa xác định</span>
      <span class="group">▪ máy cắt · ◆ dao cách ly · ⏚ tiếp địa · ◯◯ máy biến áp</span>
      <span class="group">● có nối · cắt ngang không chấm = không nối</span>
      <span class="group">lăn chuột = thu phóng · kéo = di chuyển</span>
    </div>
  </div>
</template>

<style scoped>
.canvas {
  position: relative;
  overflow: hidden;
  padding: 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
svg {
  display: block;
  flex: 1;
  width: 100%;
  min-height: 0;
  cursor: grab;
  touch-action: none;
}
svg:active {
  cursor: grabbing;
}
svg text {
  font: 11px var(--mono);
  fill: var(--dim);
}
svg text.bay {
  font-size: 12px;
  font-weight: 600;
}
svg text.tx {
  font-size: 13px;
  font-weight: 600;
  fill: var(--fg);
}
svg text.level {
  font-size: 15px;
  font-weight: 600;
  fill: var(--dim);
  opacity: 0.5;
}
.fit {
  position: absolute;
  top: 18px;
  right: 18px;
}
.legend {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: var(--dim);
  font-size: 11px;
  padding: 6px 2px 0;
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
