<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { BayDetail, Device } from '@/api/client'
import { STATE_LABEL, stateColor } from '@/components/diagram/state'

defineProps<{ bay: BayDetail; device: Device }>()
defineEmits<{ select: [deviceId: string] }>()
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
            <b :style="{ color: stateColor(device.state) }">
              {{ STATE_LABEL[device.state] }}
            </b>
          </td>
        </tr>
        <tr>
          <td>Dbpos thô</td>
          <td>{{ device.value ?? '—' }}</td>
        </tr>
        <tr>
          <td>Quality</td>
          <td>{{ device.quality }}</td>
        </tr>
        <tr>
          <td>Timestamp</td>
          <td>{{ device.source_timestamp ?? '—' }}</td>
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
      <span :style="{ color: stateColor(other.state) }">{{ STATE_LABEL[other.state] }}</span>
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
