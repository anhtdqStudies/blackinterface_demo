<script setup lang="ts">
import { computed } from 'vue'
import type { Energization, LiveState } from '@/api/client'
import { LIVE_COLOR, LIVE_LABEL, REASON_LABEL } from '@/components/diagram/state'

/**
 * What the solver concluded, and whether OneATS agrees.
 *
 * The comparison line is the important one. We compute each bay's live state
 * from the switch positions through our own bay templates; OneATS computes it
 * from the same busbars through its CheckLiveState logic. Agreement across all
 * comparable bays is the evidence that our topology is right — so it is shown,
 * not buried in a log.
 */
const props = defineProps<{ energization: Energization }>()

const ORDER: LiveState[] = ['LIVE', 'DEAD', 'EARTHED', 'UNKNOWN']

const counts = computed(() =>
  ORDER.map((state) => ({
    state,
    label: LIVE_LABEL[state],
    color: LIVE_COLOR[state],
    count: props.energization.summary[state.toLowerCase()] ?? 0,
  })).filter((row) => row.count > 0),
)

const compared = computed(() => props.energization.summary.compared ?? 0)
const mismatched = computed(() => props.energization.summary.mismatched ?? 0)

/** Sections worth a second look: anything not plainly live or plainly dead. */
const notable = computed(() =>
  props.energization.islands
    .filter((i) => i.state === 'UNKNOWN' || i.state === 'EARTHED')
    .slice(0, 8),
)

function where(island: (typeof props.energization.islands)[number]): string {
  return island.busbar_ids.join(', ') || island.bay_ids.join(', ') || island.id
}
</script>

<template>
  <section>
    <h2>Mang điện</h2>
    <div class="counts">
      <span v-for="row in counts" :key="row.state">
        <i :style="{ background: row.color }" />{{ row.label }}
        <b>{{ row.count }}</b>
      </span>
    </div>

    <p v-if="compared === 0" class="note dim">
      Không có ngăn nào đối chiếu được với <code>IsLive</code> của OneATS.
    </p>
    <p v-else-if="mismatched === 0" class="note ok">
      Khớp OneATS {{ compared }}/{{ compared }} ngăn — hai cách tính độc lập ra cùng kết quả.
    </p>
    <p v-else class="note bad">
      Lệch {{ mismatched }}/{{ compared }} ngăn so với <code>IsLive</code> của OneATS. Một trong
      hai mô hình sai — xem cảnh báo <code>energization_mismatch</code> bên dưới.
    </p>

    <template v-if="notable.length">
      <h2>Vùng cần để ý</h2>
      <div v-for="island in notable" :key="island.id" class="row">
        <span>
          {{ where(island) }}
          <small class="dim">{{ REASON_LABEL[island.reason] ?? island.reason }}</small>
        </span>
        <span class="tag" :style="{ color: LIVE_COLOR[island.state] }">
          {{ LIVE_LABEL[island.state] }}
        </span>
      </div>
    </template>
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
.counts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  font-size: 11px;
  color: var(--dim);
}
.counts i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  margin-right: 5px;
}
.counts b {
  color: var(--fg);
}
.note {
  font-size: 11px;
  margin: 8px 0 0;
  line-height: 1.5;
}
.note.ok {
  color: var(--open);
}
.note.bad {
  color: var(--closed);
}
.note.dim {
  color: var(--dim);
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 7px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  margin-bottom: 4px;
}
.row small {
  display: block;
  margin-top: 2px;
}
.tag {
  font-size: 10px;
  white-space: nowrap;
}
.dim {
  color: var(--dim);
}
</style>
