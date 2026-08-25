<script setup lang="ts">
/**
 * All switch positions in one bay — pick a device to drill down.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronRight, Cpu } from 'lucide-vue-next'
import type { BayDetail, Device } from '@/api/client'
import { device as deviceScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useWorkspaceStore } from '@/stores/workspace'
import SwitchStateBadge from '@/ui/SwitchStateBadge.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'

const props = defineProps<{ bay: BayDetail }>()

const { t } = useI18n()
const live = useLiveStore()
const workspace = useWorkspaceStore()

function stateOf(device: Device) {
  return live.deviceLive(device.id)?.state ?? device.state
}

function qualityOf(device: Device) {
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
  <div class="flex w-full flex-col gap-4">
    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="text-base font-semibold">
          {{ t('state.bayOverview', { bay: bay.id }) }}
        </CardTitle>
      </CardHeader>
      <CardContent class="grid gap-3 sm:grid-cols-2">
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('bay.voltageLevel') }}
          </p>
          <p class="mt-0.5 text-sm font-medium">{{ bay.voltage_level }}</p>
        </div>
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('bay.isLive') }}
          </p>
          <p class="mt-0.5 text-sm">{{ liveLabel }}</p>
        </div>
        <div class="sm:col-span-2">
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.bay') }}
          </p>
          <p class="mt-0.5 text-sm">
            {{ bay.name || bay.id }} — {{ bay.bay_type }}
            <span v-if="bay.template_id" class="text-muted-foreground">
              · {{ bay.template_id }}
            </span>
          </p>
        </div>
      </CardContent>
    </Card>

    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="flex items-center gap-2 text-sm font-semibold">
          <Cpu class="size-4 text-primary" />
          {{ t('bay.devices', { count: bay.devices.length }) }}
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-2 pt-0">
        <button
          v-for="device in bay.devices"
          :key="device.id"
          type="button"
          class="group flex w-full items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/40 hover:bg-muted/25"
          @click="selectDevice(device.id)"
        >
          <span>
            <span class="font-medium text-foreground">{{ device.name }}</span>
            <span class="ml-2 text-2xs text-muted-foreground">{{ device.role }}</span>
          </span>
          <span class="flex shrink-0 items-center gap-2">
            <SwitchStateBadge :state="stateOf(device)" :quality="qualityOf(device)" />
            <ChevronRight
              class="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
            />
          </span>
        </button>
      </CardContent>
    </Card>
  </div>
</template>
