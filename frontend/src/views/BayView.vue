<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  ApiError,
  api,
  type BayDetail,
  type Device,
  type Quality,
  type SwitchState,
} from '@/api/client'
import IssueList from '@/components/panels/IssueList.vue'
import { STATE_LABEL, stateColor } from '@/components/diagram/state'
import { useStationStore } from '@/stores/station'

const props = defineProps<{ bayId: string }>()

const bay = ref<BayDetail | null>(null)
const error = ref<string | null>(null)
const store = useStationStore()

// The bay was fetched once; anything that moves is read back from the live
// store, so this page does not drift away from the diagram behind it.
function stateOf(device: Device): SwitchState {
  return store.deviceLive(device.id)?.state ?? device.state
}
function qualityOf(device: Device): Quality {
  return store.deviceLive(device.id)?.quality ?? device.quality
}
function timestampOf(device: Device): string | null | undefined {
  return store.deviceLive(device.id)?.source_timestamp ?? device.source_timestamp
}
const isLive = computed(() =>
  bay.value ? (store.live?.bay_is_live[bay.value.id] ?? bay.value.is_live) : null,
)

watch(
  () => props.bayId,
  async (id) => {
    error.value = null
    try {
      bay.value = await api.bay(id)
    } catch (cause) {
      bay.value = null
      error.value = cause instanceof ApiError ? cause.message : String(cause)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="page">
    <p v-if="error" class="empty">{{ error }}</p>

    <template v-else-if="bay">
      <h1>
        {{ bay.name }} <small class="dim">— {{ bay.bay_type }}</small>
      </h1>
      <table class="head">
        <tbody>
          <tr>
            <td>Cấp điện áp</td>
            <td>{{ bay.voltage_level }}</td>
          </tr>
          <tr>
            <td>Template</td>
            <td>{{ bay.template_id ?? '—' }}</td>
          </tr>
          <tr>
            <td>IsLive</td>
            <td>
              <template v-if="isLive !== null">
                {{ isLive ? 'có điện' : 'không điện' }}
              </template>
              <template v-else>
                <span class="dim">không xác định (quality {{ bay.is_live_quality }})</span>
              </template>
            </td>
          </tr>
          <tr>
            <td>Logical nodes</td>
            <td>
              <code>{{ bay.logical_nodes.join(' ') }}</code>
            </td>
          </tr>
        </tbody>
      </table>

      <h2>Thiết bị đóng cắt ({{ bay.devices.length }})</h2>
      <table class="devices">
        <thead>
          <tr>
            <th>Tên EVN</th>
            <th>LN</th>
            <th>Vai trò</th>
            <th>Trạng thái</th>
            <th>Quality</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="device in bay.devices" :key="device.id">
            <td>
              <b>{{ device.name }}</b>
            </td>
            <td>{{ device.ln }}</td>
            <td>{{ device.role }}</td>
            <td :style="{ color: stateColor(stateOf(device)) }">
              {{ STATE_LABEL[stateOf(device)] }}
            </td>
            <td>{{ qualityOf(device) }}</td>
            <td>{{ timestampOf(device) ?? '—' }}</td>
          </tr>
        </tbody>
      </table>

      <h2>Cảnh báo của ngăn ({{ bay.issues.length }})</h2>
      <IssueList :issues="bay.issues" empty="Không có." />
    </template>
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
  overflow: auto;
  flex: 1;
}
h1 {
  font-size: 18px;
  margin: 0 0 12px;
}
h2 {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  margin: 22px 0 7px;
  font-weight: 600;
}
.head {
  max-width: 640px;
}
.devices td,
.devices th {
  width: auto;
  color: inherit;
  padding: 4px 12px 4px 0;
  text-align: left;
}
.devices th {
  color: var(--dim);
  font-weight: 600;
  border-bottom: 1px solid var(--line);
}
</style>
