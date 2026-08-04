<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Bay, Station } from '@/api/client'

defineProps<{ station: Station; bays: Bay[]; voltageLevel: string | null }>()

/**
 * "position_determined" is the number that matters for trust: how many devices
 * we can actually state a position for. A gap between it and the device count
 * means the model is showing UNDETERMINED somewhere, on purpose (I2).
 */
</script>

<template>
  <section>
    <h2>Độ phủ</h2>
    <table>
      <tbody>
        <tr>
          <td>Thiết bị đóng cắt</td>
          <td>
            <b>{{ station.coverage.devices }}</b>
          </td>
        </tr>
        <tr>
          <td>Vị trí quality GOOD</td>
          <td>
            <b>{{ station.coverage.position_good }}</b> / {{ station.coverage.devices }}
          </td>
        </tr>
        <tr>
          <td>Xác định được</td>
          <td>
            <b>{{ station.coverage.position_determined }}</b> / {{ station.coverage.devices }}
          </td>
        </tr>
        <tr>
          <td>Connectivity node</td>
          <td>{{ station.node_count }}</td>
        </tr>
      </tbody>
    </table>

    <h2>Ngăn tại {{ voltageLevel }}</h2>
    <RouterLink v-for="bay in bays" :key="bay.id" class="row" :to="`/bay/${bay.id}`">
      <span
        >{{ bay.name }}
        <small class="dim">{{ bay.template_id ?? 'không có template' }}</small></span
      >
      <span class="tag">{{ bay.bay_type }}</span>
    </RouterLink>
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
  padding: 5px 7px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  margin-bottom: 4px;
  color: var(--fg);
  text-decoration: none;
}
.row:hover {
  border-color: var(--accent);
}
.tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--dim);
}
</style>
