<script setup lang="ts">
/**
 * All switch positions in one bay — pick a device to drill down.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BayDetail, Device, Quality, SwitchState } from '@/api/client'
import { stateColor } from '@/components/diagram/state'
import { device as deviceScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useWorkspaceStore } from '@/stores/workspace'
import Field from '@/ui/Field.vue'
import Panel from '@/ui/Panel.vue'

const props = defineProps<{ bay: BayDetail }>()

const { t } = useI18n()
const live = useLiveStore()
const workspace = useWorkspaceStore()

function stateOf(device: Device): SwitchState {
  return live.deviceLive(device.id)?.state ?? device.state
}

function qualityOf(device: Device): Quality {
  return live.deviceLive(device.id)?.quality ?? device.quality
}

const liveLabel = computed(() => {
  const val = live.bayIsLive(props.bay.id)
  if (val === true) return t('bay.live')
  if (val === false) return t('bay.notLive')
  return t('bay.undetermined', { quality: props.bay.is_live_quality })
})

function selectDevice(id: string): void {
  workspace.go(deviceScope(id))
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <Panel :title="t('state.bayOverview', { bay: bay.id })">
      <Field :label="t('bay.voltageLevel')">{{ bay.voltage_level }}</Field>
      <Field :label="t('device.bay')" :numeric="false">
        {{ bay.name || bay.id }} — {{ bay.bay_type }}
      </Field>
      <Field v-if="bay.template_id" :label="t('bay.template')">{{ bay.template_id }}</Field>
      <Field :label="t('bay.isLive')">{{ liveLabel }}</Field>
    </Panel>

    <Panel :title="t('bay.devices', { count: bay.devices.length })">
      <button
        v-for="device in bay.devices"
        :key="device.id"
        type="button"
        class="mb-1 flex w-full items-center justify-between gap-2 rounded-[var(--radius)] border border-line px-2 py-1.5 text-left text-sm hover:border-accent"
        @click="selectDevice(device.id)"
      >
        <span>
          {{ device.name }}
          <small class="text-dim">{{ device.role }}</small>
        </span>
        <span
          class="text-2xs whitespace-nowrap"
          :style="{ color: stateColor(stateOf(device)) }"
        >
          {{ t(`state.${stateOf(device)}`) }}
          <span class="text-dim"> · {{ qualityOf(device) }}</span>
        </span>
      </button>
    </Panel>
  </div>
</template>
