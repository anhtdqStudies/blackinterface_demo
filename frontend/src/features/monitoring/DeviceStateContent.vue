<script setup lang="ts">
/**
 * What one device is doing, in the operator's vocabulary.
 *
 * **No NodeId, no raw Dbpos, no logical-node name** (ADR-0014 §8, screens.md §1,
 * `check.py` §5). Those belong to the `binding` pane on the engineer surface.
 * They were here until GD 1.5 lô 3 because the pane this replaced was written
 * before the rule existed; keeping them would have put protocol detail on the
 * screen somebody reads while switching a live station, where every extra field
 * is one more thing between them and the answer.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { BayDetail, Device, Quality, SwitchState } from '@/api/client'
import { stateColor } from '@/components/diagram/state'
import { bayScope, opsPath } from '@/router'
import { useLiveStore } from '@/stores/live'
import Field from '@/ui/Field.vue'
import Panel from '@/ui/Panel.vue'

const props = defineProps<{ bay: BayDetail; device: Device }>()
defineEmits<{ select: [deviceId: string] }>()

const { t } = useI18n()
const live = useLiveStore()

function stateOf(device: Device): SwitchState {
  return live.deviceLive(device.id)?.state ?? device.state
}

function qualityOf(device: Device): Quality {
  return live.deviceLive(device.id)?.quality ?? device.quality
}

const current = computed(() => live.deviceLive(props.device.id))
const timestamp = computed(
  () => current.value?.source_timestamp ?? props.device.source_timestamp,
)
</script>

<template>
  <div>
    <Panel :title="t('device.title')">
      <Field :label="t('device.evnName')">
        <b>{{ device.name }}</b>
      </Field>
      <Field :label="t('device.bay')" :numeric="false">
        <RouterLink :to="opsPath(bayScope(bay.id))">{{ bay.id }}</RouterLink>
        — {{ bay.bay_type }}
      </Field>
      <Field :label="t('device.role')">{{ device.role }}</Field>
      <Field :label="t('device.state')">
        <b :style="{ color: stateColor(stateOf(device)) }">
          {{ t(`state.${stateOf(device)}`) }}
        </b>
      </Field>
      <Field :label="t('device.quality')">{{ qualityOf(device) }}</Field>
      <Field :label="t('device.timestamp')">{{ timestamp ?? t('common.dash') }}</Field>
      <Field :label="t('device.connectsTo')" :numeric="false">
        <div v-for="node in device.terminals" :key="node">{{ node }}</div>
      </Field>
    </Panel>

    <Panel :title="t('device.inBay', { bay: bay.id, count: bay.devices.length })">
      <button
        v-for="other in bay.devices"
        :key="other.id"
        type="button"
        class="mb-1 flex w-full items-center justify-between gap-2 rounded-[var(--radius)] border border-line px-2 py-1 text-left text-sm hover:border-accent"
        :class="{ 'border-accent bg-panel-2': other.id === device.id }"
        @click="$emit('select', other.id)"
      >
        <span>
          {{ other.name }}
          <small class="text-dim">{{ other.role }}</small>
        </span>
        <span class="text-2xs whitespace-nowrap" :style="{ color: stateColor(stateOf(other)) }">
          {{ t(`state.${stateOf(other)}`) }}
        </span>
      </button>
    </Panel>
  </div>
</template>
