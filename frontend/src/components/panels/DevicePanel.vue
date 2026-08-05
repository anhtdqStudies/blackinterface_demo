<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { BayDetail, Device, Quality, SwitchState } from '@/api/client'
import { STATE_LABEL, stateColor } from '@/components/diagram/state'
import { useStationStore } from '@/stores/station'

/**
 * `bay` was fetched once, when the device was clicked. Its positions are
 * therefore as old as that click, so every field that can move is read back
 * from the live store instead — otherwise the panel would quietly contradict
 * the diagram right next to it.
 */
const props = defineProps<{ bay: BayDetail; device: Device }>()
defineEmits<{ select: [deviceId: string] }>()

const store = useStationStore()

function stateOf(device: Device): SwitchState {
  return store.deviceLive(device.id)?.state ?? device.state
}
function qualityOf(device: Device): Quality {
  return store.deviceLive(device.id)?.quality ?? device.quality
}
const current = computed(() => store.deviceLive(props.device.id))
const timestamp = computed(
  () => current.value?.source_timestamp ?? props.device.source_timestamp,
)
const raw = computed(() => current.value?.value ?? props.device.value)
</script>

<template>
  <section>
    <h2>Thiết bị</h2>
    <table>
      <tbody>
        <tr>
          <td>Tên EVN</td>
          <td>
            <b>{{ device.name }}</b>
          </td>
        </tr>
        <tr>
          <td>Ngăn</td>
          <td>
            <RouterLink :to="`/bay/${bay.id}`">{{ bay.id }}</RouterLink> — {{ bay.bay_type }}
          </td>
        </tr>
        <tr>
          <td>Logical node</td>
          <td>{{ device.ln }}</td>
        </tr>
        <tr>
          <td>Vai trò</td>
          <td>{{ device.role }}</td>
        </tr>
        <tr>
          <td>Trạng thái</td>
          <td>
            <b :style="{ color: stateColor(stateOf(device)) }">
              {{ STATE_LABEL[stateOf(device)] }}
            </b>
          </td>
        </tr>
        <tr>
          <td>Dbpos thô</td>
          <td>{{ raw ?? '—' }}</td>
        </tr>
        <tr>
          <td>Quality</td>
          <td>{{ qualityOf(device) }}</td>
        </tr>
        <tr>
          <td>Timestamp</td>
          <td>{{ timestamp ?? '—' }}</td>
        </tr>
        <tr>
          <td>Nối tới</td>
          <td>
            <div v-for="node in device.terminals" :key="node">{{ node }}</div>
          </td>
        </tr>
        <tr>
          <td>source_ref</td>
          <td>
            <code>{{ device.source_ref ?? '—' }}</code>
          </td>
        </tr>
      </tbody>
    </table>

    <h2>Ngăn {{ bay.id }} — {{ bay.devices.length }} thiết bị</h2>
    <button
      v-for="other in bay.devices"
      :key="other.id"
      class="row"
      :class="{ on: other.id === device.id }"
      @click="$emit('select', other.id)"
    >
      <span
        >{{ other.name }} <small class="dim">{{ other.ln }}</small></span
      >
      <span :style="{ color: stateColor(stateOf(other)) }">{{
        STATE_LABEL[stateOf(other)]
      }}</span>
    </button>
  </section>
</template>

<style scoped>
h2 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  margin: 16px 0 7px;
  font-weight: 600;
}
h2:first-child {
  margin-top: 0;
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  margin-bottom: 4px;
  text-align: left;
}
</style>
