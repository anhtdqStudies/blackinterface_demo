<script setup lang="ts">
/**
 * Switch positions for whatever scope this pane is aimed at.
 *
 * Reads **its own `scope` prop**, not `workspace.scope` — a pinned pane must
 * not silently ignore its pin (ADR-0014 §3).
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApiError, api, type BayDetail } from '@/api/client'
import DeviceStateContent from '@/features/monitoring/DeviceStateContent.vue'
import type { PaneProps } from '@/app/layout/panes'
import { device as deviceScope, parentScope } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import Skeleton from '@/ui/Skeleton.vue'

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

const deviceId = computed<string | null>(() =>
  props.scope.kind === 'device' ? props.scope.id : null,
)

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
  <div class="p-3">
    <Skeleton v-if="loading" variant="row" :count="6" />
    <ErrorBox v-else-if="error" :code="error.code" :message="error.message" @retry="retry" />
    <DeviceStateContent
      v-else-if="bay && device"
      :bay="bay"
      :device="device"
      @select="workspace.go(deviceScope($event))"
    />
    <Empty v-else-if="bay" :reason="t('pane.pickDevice', { bay: bay.id })" />
    <Empty v-else :reason="t('pane.pickBay')" />
  </div>
</template>
