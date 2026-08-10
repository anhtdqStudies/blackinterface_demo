<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import SldCanvas from '@/components/diagram/SldCanvas.vue'
import { bay as bayScope, device as deviceScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Card, CardContent } from '@/ui/card'

const { t } = useI18n()
const structure = useStructureStore()
const live = useLiveStore()
const workspace = useWorkspaceStore()

const canvas = ref<InstanceType<typeof SldCanvas> | null>(null)

watch(
  () => structure.diagram,
  async () => {
    await nextTick()
    canvas.value?.fit()
  },
)

function retry(): void {
  void structure.load()
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <PaneSkeleton v-if="structure.loading" variant="block" class="flex-1" />
    <ErrorBox
      v-else-if="structure.error"
      :code="structure.error.code"
      :message="structure.error.message"
      @retry="retry"
    />
    <Card v-else-if="structure.diagram" class="min-h-0 flex-1 overflow-hidden rounded-xl py-0">
      <CardContent class="h-full min-h-0 p-2">
        <SldCanvas
          ref="canvas"
          :diagram="structure.diagram"
          :node-state="live.energization?.node_state ?? {}"
          :device-state="live.state?.devices ?? {}"
          :selected-device-id="workspace.deviceId"
          @select="workspace.go(deviceScope($event))"
          @select-bay="workspace.go(bayScope($event))"
        />
      </CardContent>
    </Card>
    <Empty v-else :reason="t('ops.noDiagram')" />
  </div>
</template>
