<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Maximize2, Minimize2, ZoomIn, ZoomOut } from 'lucide-vue-next'
import SldCanvas from '@/components/diagram/SldCanvas.vue'
import { bay as bayScope, device as deviceScope } from '@/scope'
import { useLiveStore } from '@/stores/live'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Button } from '@/ui/button'
import { Card, CardContent } from '@/ui/card'

const { t } = useI18n()
const structure = useStructureStore()
const live = useLiveStore()
const workspace = useWorkspaceStore()

const root = ref<HTMLElement | null>(null)
const canvas = ref<InstanceType<typeof SldCanvas> | null>(null)
const isFullscreen = ref(false)

watch(
  () => structure.diagram,
  async () => {
    await nextTick()
    canvas.value?.fit()
  },
)

function onFullscreenChange(): void {
  isFullscreen.value = document.fullscreenElement === root.value
  void nextTick(() => canvas.value?.fit())
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})

function retry(): void {
  void structure.load()
}

function fit(): void {
  canvas.value?.fit()
}

function zoomIn(): void {
  canvas.value?.zoomIn()
}

function zoomOut(): void {
  canvas.value?.zoomOut()
}

async function toggleFullscreen(): Promise<void> {
  if (!root.value) return
  if (document.fullscreenElement === root.value) {
    await document.exitFullscreen()
    return
  }
  await root.value.requestFullscreen()
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
    <div
      v-else-if="structure.diagram"
      ref="root"
      class="sld-root flex min-h-0 flex-1 flex-col"
      :class="{ 'sld-root--fullscreen': isFullscreen }"
    >
      <Card
        class="flex min-h-0 flex-1 flex-col gap-0 overflow-hidden rounded-xl py-0"
        :class="{ 'sld-card--fullscreen': isFullscreen }"
      >
        <div
          class="sld-toolbar flex shrink-0 flex-wrap items-center gap-2 border-b border-border/60 bg-muted/20 px-3 py-2"
          :class="{ 'sld-toolbar--overlay': isFullscreen }"
        >
          <span v-if="isFullscreen" class="sld-title">{{ t('pane.sld') }}</span>
          <Button variant="outline" size="sm" class="gap-1.5" @click="fit">
            <Maximize2 class="size-3.5" />
            {{ t('sld.fit') }}
          </Button>
          <Button variant="outline" size="icon-sm" :title="t('sld.zoomIn')" @click="zoomIn">
            <ZoomIn />
          </Button>
          <Button variant="outline" size="icon-sm" :title="t('sld.zoomOut')" @click="zoomOut">
            <ZoomOut />
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="gap-1.5"
            :title="isFullscreen ? t('sld.exitFullscreen') : t('sld.fullscreen')"
            @click="toggleFullscreen"
          >
            <Minimize2 v-if="isFullscreen" class="size-3.5" />
            <Maximize2 v-else class="size-3.5" />
            {{ isFullscreen ? t('sld.exitFullscreen') : t('sld.fullscreen') }}
          </Button>
          <span v-if="!isFullscreen" class="ml-auto text-2xs text-muted-foreground">
            {{ t('sld.hint') }}
          </span>
        </div>
        <CardContent class="flex min-h-0 flex-1 flex-col p-0">
          <SldCanvas
            ref="canvas"
            :diagram="structure.diagram"
            :node-state="live.energization?.node_state ?? {}"
            :device-state="live.state?.devices ?? {}"
            :selected-device-id="workspace.deviceId"
            :compact="isFullscreen"
            @select="workspace.go(deviceScope($event))"
            @select-bay="workspace.go(bayScope($event))"
          />
        </CardContent>
      </Card>
    </div>
    <Empty v-else :reason="t('ops.noDiagram')" />
  </div>
</template>

<style scoped>
.sld-root--fullscreen {
  background: var(--background);
}

.sld-card--fullscreen {
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.sld-toolbar--overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 3;
  border: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--background) 88%, transparent);
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 28px color-mix(in srgb, var(--background) 35%, transparent);
}

.sld-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--foreground);
  margin-right: 4px;
  padding-right: 8px;
  border-right: 1px solid var(--border);
}

.sld-root--fullscreen .sld-card--fullscreen {
  position: relative;
}
</style>
