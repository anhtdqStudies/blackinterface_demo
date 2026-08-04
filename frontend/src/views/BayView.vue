<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError, api, type BayDetail } from '@/api/client'
import IssueList from '@/components/panels/IssueList.vue'
import { STATE_LABEL, stateColor } from '@/components/diagram/state'

const props = defineProps<{ bayId: string }>()

const bay = ref<BayDetail | null>(null)
const error = ref<string | null>(null)

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
              <template v-if="bay.is_live_quality === 'GOOD'">
                {{ bay.is_live ? 'có điện' : 'không điện' }}
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
            <td :style="{ color: stateColor(device.state) }">
              {{ STATE_LABEL[device.state] }}
            </td>
            <td>{{ device.quality }}</td>
            <td>{{ device.source_timestamp ?? '—' }}</td>
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
