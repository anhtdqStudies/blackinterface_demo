<script setup lang="ts">
/**
 * Switch positions for whatever scope this pane is aimed at.
 *
 * Reads **its own `scope` prop**, not `workspace.scope` — a pinned pane must
 * not silently ignore its pin (ADR-0014 §3).
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Activity } from 'lucide-vue-next'
import { ApiError, api, type BayDetail } from '@/api/client'
import BayStateContent from '@/features/monitoring/BayStateContent.vue'
import DeviceStateContent from '@/features/monitoring/DeviceStateContent.vue'
import StationStateContent from '@/features/monitoring/StationStateContent.vue'
import type { PaneProps } from '@/app/layout/panes'
import { device as deviceScope, formatScope, parentScope } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const structure = useStructureStore()
const workspace = useWorkspaceStore()

const bayId = computed<string | null>(() => {
  const s = props.scope
  if (s.kind === 'bay') return s.id
  if (s.kind !== 'device' && s.kind !== 'point') return null
  const up = parentScope(s)
  const parent = up?.kind === 'device' ? parentScope(up) : up
  return parent?.kind === 'bay' ? parent.id : null
})

const deviceId = computed<string | null>(() => {
  const s = props.scope
  if (s.kind === 'device') return s.id
  if (s.kind === 'point') {
    const parent = parentScope(s)
    return parent?.kind === 'device' ? parent.id : null
  }
  return null
})

const showStation = computed(() => props.scope.kind === 'station' || props.scope.kind === 'vl')

const voltageFilter = computed(() => (props.scope.kind === 'vl' ? props.scope.id : null))

const scopeLabel = computed(() => formatScope(props.scope))

const bay = ref<BayDetail | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)

watch(
  () => [bayId.value, structure.generation] as const,
  async ([id]) => {
    if (!id) {
      bay.value = null
      error.value = null
      return
    }
    if (bay.value?.id === id) return
    loading.value = true
    error.value = null
    try {
      bay.value = await api.bay(id)
    } catch (cause) {
      bay.value = null
      error.value =
        cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

const device = computed(() => {
  const id = deviceId.value
  return id ? (bay.value?.devices.find((d) => d.id === id) ?? null) : null
})

function retry(): void {
  const id = bayId.value
  if (id) void api.bay(id).then((next) => (bay.value = next))
}
</script>

<template>
  <div class="w-full space-y-4">
    <div
      v-if="!showStation || structure.bays.length"
      class="rounded-lg border border-border/60 bg-muted/20 px-4 py-2.5"
    >
      <p class="flex items-center gap-2 text-sm text-muted-foreground">
        <Activity class="size-4 shrink-0 text-primary" />
        {{ t('state.scopeLine', { scope: scopeLabel }) }}
      </p>
    </div>

    <StationStateContent
      v-if="showStation && structure.bays.length"
      :voltage-filter="voltageFilter"
    />
    <Empty v-else-if="showStation" :reason="t('pane.noModel')" />

    <template v-else-if="props.scope.kind === 'bay' || deviceId">
      <PaneSkeleton v-if="loading" variant="row" :count="6" />
      <ErrorBox v-else-if="error" :code="error.code" :message="error.message" @retry="retry" />
      <DeviceStateContent
        v-else-if="bay && device"
        :bay="bay"
        :device="device"
        @select="workspace.go(deviceScope($event))"
      />
      <BayStateContent v-else-if="bay" :bay="bay" />
      <Empty v-else :reason="t('pane.pickBay')" />
    </template>

    <Empty v-else :reason="t('state.scopeUnsupported')" />
  </div>
</template>
