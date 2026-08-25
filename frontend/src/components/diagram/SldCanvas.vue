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
  /** Compact overlay legend for fullscreen / large canvas. */
  compact?: boolean
}>()
defineEmits<{ select: [deviceId: string]; selectBay: [bayId: string] }>()

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

function zoomBy(factor: number): void {
  const vb = viewBox.value
  const cx = vb.x + vb.w / 2
  const cy = vb.y + vb.h / 2
  viewBox.value = {
    x: cx - (vb.w * factor) / 2,
    y: cy - (vb.h * factor) / 2,
    w: vb.w * factor,
    h: vb.h * factor,
  }
}

function zoomIn(): void {
  zoomBy(1 / 1.2)
}

function zoomOut(): void {
  zoomBy(1.2)
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

defineExpose({ focusSection, fit, zoomIn, zoomOut })

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
  const target = event.target as Element
  if (target.closest('.sym, .bay-col')) return
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

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  window.addEventListener('keydown', onKey)
  const el = svgEl.value
  if (el) {
    resizeObserver = new ResizeObserver(() => fit())
    resizeObserver.observe(el)
  }
  fit()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  resizeObserver?.disconnect()
})
</script>

<template>
  <div class="canvas" :class="{ compact }">
    <svg
      ref="svgEl"
      class="sld-svg"
      :viewBox="`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`"
      preserveAspectRatio="xMidYMid meet"
      shape-rendering="geometricPrecision"
      text-rendering="geometricPrecision"
      @wheel="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @click.capture="swallowDragClick"
    >
      <defs>
        <pattern id="sld-grid" :width="40" :height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--sld-grid)" stroke-width="0.5" />
        </pattern>
      </defs>

      <!-- Deep canvas — matches SCADA single-line background. -->
      <rect
        class="sld-bg"
        :x="viewBox.x"
        :y="viewBox.y"
        :width="viewBox.w"
        :height="viewBox.h"
        fill="var(--sld-canvas)"
      />
      <rect
        :x="viewBox.x"
        :y="viewBox.y"
        :width="viewBox.w"
        :height="viewBox.h"
        fill="url(#sld-grid)"
        opacity="0.55"
      />

      <!-- Bay columns: faint dashed frames like Grid Designer. -->
      <g class="bay-frames">
        <rect
          v-for="column in diagram.columns"
          :key="`frame-${column.bay_id}`"
          :x="column.x - 52"
          :y="column.top - 8"
          width="104"
          :height="column.bottom - column.top + 16"
          rx="3"
          fill="none"
          stroke="var(--sld-frame)"
          stroke-width="1"
          stroke-dasharray="4 6"
        />
      </g>

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
          :stroke-width="rail.transfer ? 3 : 4"
          stroke-linecap="butt"
          vector-effect="non-scaling-stroke"
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
        stroke-width="1.5"
        vector-effect="non-scaling-stroke"
      />

      <!-- Junction dot = really connected. No dot = the conductor just crosses. -->
      <circle
        v-for="junction in diagram.junctions"
        :key="junction.id"
        :cx="junction.x"
        :cy="junction.y"
        r="3.5"
        vector-effect="non-scaling-stroke"
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
      <g
        v-for="column in diagram.columns"
        :key="column.bay_id"
        class="bay-col"
        @click.stop="$emit('selectBay', column.bay_id)"
      >
        <rect
          class="bay-hit"
          :x="column.x - 45"
          :y="column.top"
          width="90"
          :height="column.bottom - column.top"
          fill="transparent"
        />
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

    <div class="legend" :class="{ 'legend-compact': compact }">
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
      <span v-if="!compact" class="group"
        >▪ máy cắt · ◆ dao cách ly · ⏚ tiếp địa · ◯◯ máy biến áp</span
      >
      <span v-if="!compact" class="group">● có nối · cắt ngang không chấm = không nối</span>
      <span class="group">lăn chuột = thu phóng · kéo = di chuyển</span>
    </div>
  </div>
</template>

<style scoped>
.canvas {
  --sld-canvas: #06080c;
  --sld-grid: color-mix(in srgb, var(--foreground) 7%, transparent);
  --sld-frame: color-mix(in srgb, var(--foreground) 14%, transparent);

  position: relative;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.canvas.compact .legend {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  border: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
  border-radius: var(--radius-md);
  padding: 6px 10px;
  background: color-mix(in srgb, var(--background) 82%, transparent);
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--background) 40%, transparent);
}
.sld-svg {
  display: block;
  flex: 1;
  width: 100%;
  min-height: 0;
  cursor: grab;
  touch-action: none;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.sld-svg:active {
  cursor: grabbing;
}
.sld-bg {
  pointer-events: none;
}
.bay-frames {
  pointer-events: none;
}
.sld-svg text {
  font: 11px var(--font-sans);
  fill: var(--dim);
  letter-spacing: 0.02em;
}
.sld-svg text.bay {
  font-size: 13px;
  font-weight: 600;
  fill: var(--fg);
}
.sld-svg text.tx {
  font-size: 14px;
  font-weight: 600;
  fill: var(--fg);
}
.sld-svg text.level {
  font-size: 16px;
  font-weight: 600;
  fill: var(--dim);
  opacity: 0.45;
}
.legend {
  display: flex;
  gap: 10px 14px;
  flex-wrap: wrap;
  color: var(--muted-foreground);
  font-size: 11px;
  border-top: 1px solid var(--border);
  padding: 8px 12px;
  background: color-mix(in srgb, var(--muted) 25%, transparent);
}
.legend-compact {
  gap: 6px 10px;
  font-size: 10px;
  border-top: none;
}
.legend i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  margin-right: 5px;
}
.legend .group {
  color: var(--foreground);
  opacity: 0.75;
}
.bay-col {
  cursor: pointer;
}
.bay-col:hover text.bay {
  fill: var(--accent);
}
</style>
