<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type BayDetail, type Device } from '@/api/client'
import SldCanvas from '@/components/diagram/SldCanvas.vue'
import CoveragePanel from '@/components/panels/CoveragePanel.vue'
import DevicePanel from '@/components/panels/DevicePanel.vue'
import IssueList from '@/components/panels/IssueList.vue'
import { useStationStore } from '@/stores/station'

const store = useStationStore()
const selectedBay = ref<BayDetail | null>(null)
const selectedDevice = ref<Device | null>(null)

async function select(deviceId: string): Promise<void> {
  const bayId = deviceId.split('.')[0]
  if (!bayId) return
  const bay = selectedBay.value?.id === bayId ? selectedBay.value : await api.bay(bayId)
  selectedBay.value = bay
  selectedDevice.value = bay.devices.find((d) => d.id === deviceId) ?? null
}

function clearSelection(): void {
  selectedBay.value = null
  selectedDevice.value = null
}

// The drawing shows every voltage level at once, so the tabs only move the eye
// and re-aim the side panel.
function goToLevel(level: string): void {
  store.selectVoltageLevel(level)
  clearSelection()
  const section = store.diagram?.sections.find((s) => s.voltage_level === level)
  const canvas = document.querySelector('.canvas')
  if (section && canvas) canvas.scrollTo({ top: section.top, behavior: 'smooth' })
}

watch(() => store.voltageLevel, clearSelection)
</script>

<template>
  <div class="layout">
    <div class="main">
      <div class="tabs">
        <button
          v-for="level in store.voltageLevels"
          :key="level"
          :class="{ on: level === store.voltageLevel }"
          @click="goToLevel(level)"
        >
          {{ level }}
        </button>
      </div>

      <SldCanvas
        v-if="store.diagram"
        :diagram="store.diagram"
        :selected-device-id="selectedDevice?.id ?? null"
        @select="select"
      />
      <p v-else-if="!store.loading" class="empty pad">Chưa có sơ đồ để hiển thị.</p>
    </div>

    <aside>
      <template v-if="selectedBay && selectedDevice">
        <DevicePanel :bay="selectedBay" :device="selectedDevice" @select="select" />
        <button class="back" @click="clearSelection">← Về tổng quan</button>
      </template>

      <template v-else-if="store.station">
        <CoveragePanel
          :station="store.station"
          :bays="store.baysHere"
          :voltage-level="store.voltageLevel"
        />
        <h2>Cảnh báo dựng model ({{ store.issues.length }})</h2>
        <IssueList :issues="store.issues" empty="Không có. Mọi ngăn khớp template." />
      </template>
    </aside>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  flex: 1;
  min-height: 0;
}
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
.tabs {
  display: flex;
  gap: 8px;
  padding: 10px 12px 0;
}
aside {
  border-left: 1px solid var(--line);
  background: var(--panel);
  overflow: auto;
  padding: 12px;
}
aside h2 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  margin: 16px 0 7px;
  font-weight: 600;
}
.back {
  margin-top: 12px;
}
.pad {
  padding: 12px;
}
</style>
