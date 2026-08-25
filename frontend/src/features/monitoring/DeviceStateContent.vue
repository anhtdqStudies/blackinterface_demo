<script setup lang="ts">
/**
 * What one device is doing, in the operator's vocabulary.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ChevronRight, Cpu } from 'lucide-vue-next'
import type { BayDetail, Device } from '@/api/client'
import { cn } from '@/lib/utils'
import { bayScope, opsPath } from '@/router'
import { useLiveStore } from '@/stores/live'
import SwitchStateBadge from '@/ui/SwitchStateBadge.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'

const props = defineProps<{ bay: BayDetail; device: Device }>()
defineEmits<{ select: [deviceId: string] }>()

const { t } = useI18n()
const live = useLiveStore()

function stateOf(device: Device) {
  return live.deviceLive(device.id)?.state ?? device.state
}

function qualityOf(device: Device) {
  return live.deviceLive(device.id)?.quality ?? device.quality
}

const current = computed(() => live.deviceLive(props.device.id))
const timestamp = computed(
  () => current.value?.source_timestamp ?? props.device.source_timestamp,
)
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="text-base font-semibold">{{ t('device.title') }}</CardTitle>
      </CardHeader>
      <CardContent class="grid gap-4 sm:grid-cols-2">
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.evnName') }}
          </p>
          <p class="mt-0.5 text-sm font-semibold">{{ device.name }}</p>
        </div>
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.role') }}
          </p>
          <p class="mt-0.5 text-sm">{{ device.role }}</p>
        </div>
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.bay') }}
          </p>
          <p class="mt-0.5 text-sm">
            <RouterLink :to="opsPath(bayScope(bay.id))" class="text-primary hover:underline">
              {{ bay.id }}
            </RouterLink>
            — {{ bay.bay_type }}
          </p>
        </div>
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.state') }}
          </p>
          <div class="mt-1">
            <SwitchStateBadge :state="stateOf(device)" :quality="qualityOf(device)" />
          </div>
        </div>
        <div>
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.timestamp') }}
          </p>
          <p class="mt-0.5 font-mono text-sm tabular-nums">
            {{ timestamp ?? t('common.dash') }}
          </p>
        </div>
        <div v-if="device.terminals.length" class="sm:col-span-2">
          <p class="text-2xs tracking-wide text-muted-foreground uppercase">
            {{ t('device.connectsTo') }}
          </p>
          <ul class="mt-1 space-y-0.5 font-mono text-2xs text-muted-foreground">
            <li v-for="node in device.terminals" :key="node">{{ node }}</li>
          </ul>
        </div>
      </CardContent>
    </Card>

    <Card class="rounded-xl border-border/70 shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="flex items-center gap-2 text-sm font-semibold">
          <Cpu class="size-4 text-primary" />
          {{ t('device.inBay', { bay: bay.id, count: bay.devices.length }) }}
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-2 pt-0">
        <button
          v-for="other in bay.devices"
          :key="other.id"
          type="button"
          class="group flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors"
          :class="
            cn(
              other.id === device.id
                ? 'border-primary/50 bg-primary/5'
                : 'border-border/60 bg-muted/10 hover:border-primary/40 hover:bg-muted/25',
            )
          "
          @click="$emit('select', other.id)"
        >
          <span>
            <span class="font-medium text-foreground">{{ other.name }}</span>
            <span class="ml-2 text-2xs text-muted-foreground">{{ other.role }}</span>
          </span>
          <span class="flex shrink-0 items-center gap-2">
            <SwitchStateBadge :state="stateOf(other)" />
            <ChevronRight
              v-if="other.id !== device.id"
              class="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
            />
          </span>
        </button>
      </CardContent>
    </Card>
  </div>
</template>
