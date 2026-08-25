<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'
import { ApiError, api, type BayDetail } from '@/api/client'
import BayStateContent from '@/features/monitoring/BayStateContent.vue'
import DeviceStateContent from '@/features/monitoring/DeviceStateContent.vue'
import { device as deviceScope, formatScope, type ScopeRef } from '@/scope'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Button } from '@/ui/button'

const props = defineProps<{ scope: ScopeRef }>()

const { t } = useI18n()
const workspace = useWorkspaceStore()

const bayId = computed<string | null>(() => {
  const s = props.scope
  if (s.kind === 'bay') return s.id
  if (s.kind === 'device') return s.id.split('.')[0] ?? null
  return null
})

const deviceId = computed<string | null>(() =>
  props.scope.kind === 'device' ? props.scope.id : null,
)

const bay = ref<BayDetail | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)

watch(
  bayId,
  async (id) => {
    if (!id) {
      bay.value = null
      error.value = null
      return
    }
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
  <aside
    class="flex h-full min-h-0 w-full min-w-0 flex-col border-l border-border bg-card/10"
    :aria-label="t('workspace.details')"
  >
    <div
      class="flex shrink-0 items-center gap-2 border-b border-border/60 px-3 py-2 text-xs text-muted-foreground"
    >
      <span class="min-w-0 flex-1 truncate font-medium text-foreground">
        {{ t('workspace.detailsTitle') }}
      </span>
      <Button
        variant="ghost"
        size="icon-xs"
        :title="t('workspace.detailsClose')"
        @click="workspace.dismissDetails()"
      >
        <X class="size-3.5" />
      </Button>
    </div>

    <div class="min-h-0 flex-1 overflow-auto p-3">
      <p class="mb-3 font-mono text-2xs text-muted-foreground">{{ formatScope(scope) }}</p>

      <PaneSkeleton v-if="loading" variant="row" :count="4" />
      <ErrorBox v-else-if="error" :code="error.code" :message="error.message" @retry="retry" />
      <DeviceStateContent
        v-else-if="bay && device"
        :bay="bay"
        :device="device"
        @select="workspace.go(deviceScope($event))"
      />
      <BayStateContent v-else-if="bay" :bay="bay" />
      <Empty v-else :reason="t('pane.pickBay')" />
    </div>
  </aside>
</template>
