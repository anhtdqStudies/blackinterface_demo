<script setup lang="ts">
/**
 * The single-line diagram. Clicking a device updates workspace scope (ADR-0010).
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SldCanvas from '@/components/diagram/SldCanvas.vue'
import { bay as bayScope, device as deviceScope, voltageLevel as vlScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import Skeleton from '@/ui/Skeleton.vue'

const { t } = useI18n()
const structure = useStructureStore()
const live = useLiveStore()
const workspace = useWorkspaceStore()

const canvas = ref<InstanceType<typeof SldCanvas> | null>(null)

function goToLevel(level: string): void {
  workspace.go(vlScope(level))
  const section = structure.diagram?.sections.find((s) => s.voltage_level === level)
  if (section) canvas.value?.focusSection(section.top, section.bottom)
}

function retry(): void {
  void structure.load()
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div v-if="structure.voltageLevels.length" class="flex shrink-0 gap-2 px-3 pt-2">
      <button
        v-for="level in structure.voltageLevels"
        :key="level"
        :class="{ on: level === workspace.voltageLevel }"
        @click="goToLevel(level)"
      >
        {{ level }}
      </button>
    </div>

    <Skeleton v-if="structure.loading" variant="block" class="m-3 flex-1" />
    <ErrorBox
      v-else-if="structure.error"
      class="m-3"
      :code="structure.error.code"
      :message="structure.error.message"
      @retry="retry"
    />
    <SldCanvas
      v-else-if="structure.diagram"
      ref="canvas"
      :diagram="structure.diagram"
      :node-state="live.energization?.node_state ?? {}"
      :device-state="live.state?.devices ?? {}"
      :selected-device-id="workspace.deviceId"
      @select="workspace.go(deviceScope($event))"
      @select-bay="workspace.go(bayScope($event))"
    />
    <Empty v-else :reason="t('ops.noDiagram')" />
  </div>
</template>
