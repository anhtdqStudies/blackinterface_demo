<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import {
  isLayoutRowPane,
  isLayoutRowTabs,
  PANE_COMPONENTS,
  type Layout,
  type Pane,
} from './panes'
import PaneFrame from './PaneFrame.vue'
import WorkspaceTabs from './WorkspaceTabs.vue'
import type { ScopeRef } from '@/scope'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<{
  layout: Layout
  storageKey: string
  scopeFor: (pane: Pane) => ScopeRef
}>()

const workspace = useWorkspaceStore()

const CHAT_COLLAPSED_SIZE = 4

const chatPanelRef = ref<{ collapse: () => void; expand: () => void } | null>(null)

function setChatPanel(el: unknown): void {
  if (el && typeof el === 'object' && 'collapse' in el && 'expand' in el) {
    chatPanelRef.value = el as { collapse: () => void; expand: () => void }
  } else {
    chatPanelRef.value = null
  }
}

const saveId = (suffix = ''): string => `bi.layout.${props.storageKey}${suffix}`

async function applyChatCollapsed(): Promise<void> {
  await nextTick()
  const panel = chatPanelRef.value
  if (!panel) return
  if (workspace.chatCollapsed) panel.collapse()
  else panel.expand()
}

onMounted(() => {
  void applyChatCollapsed()
})

watch(
  () => workspace.chatCollapsed,
  () => {
    void applyChatCollapsed()
  },
)

function isChatColumn(colIndex: number, pane: Pane): boolean {
  return colIndex === 0 && pane.kind === 'chat'
}
</script>

<template>
  <SplitterGroup
    direction="horizontal"
    :auto-save-id="saveId()"
    class="flex min-h-0 flex-1 gap-2 bg-background p-2"
  >
    <template v-for="(col, ci) in layout.cols" :key="ci">
      <SplitterResizeHandle
        v-if="ci > 0"
        class="w-px shrink-0 bg-border transition-colors data-[state=drag]:bg-primary hover:bg-primary/60"
      />
      <SplitterPanel
        :default-size="col.size"
        :min-size="ci === 0 ? 28 : 12"
        class="flex min-w-0 flex-col"
      >
        <SplitterGroup
          direction="vertical"
          :auto-save-id="saveId(`.c${ci}`)"
          class="min-h-0 flex-1 gap-2"
        >
          <template v-for="(row, ri) in col.rows" :key="ri">
            <SplitterResizeHandle
              v-if="ri > 0"
              class="h-px shrink-0 bg-border transition-colors data-[state=drag]:bg-primary hover:bg-primary/60"
            />

            <SplitterPanel
              v-if="isLayoutRowPane(row) && isChatColumn(ci, row.pane)"
              :id="`chat-col-${ci}`"
              :ref="setChatPanel"
              :default-size="row.size"
              :min-size="CHAT_COLLAPSED_SIZE"
              collapsible
              :collapsed-size="CHAT_COLLAPSED_SIZE"
              class="min-h-0"
            >
              <PaneFrame :pane="row.pane" :scope="scopeFor(row.pane)">
                <component
                  :is="PANE_COMPONENTS[row.pane.kind]"
                  :pane="row.pane"
                  :scope="scopeFor(row.pane)"
                />
              </PaneFrame>
            </SplitterPanel>

            <SplitterPanel
              v-else-if="isLayoutRowPane(row)"
              :default-size="row.size"
              :min-size="10"
              class="min-h-0"
            >
              <PaneFrame :pane="row.pane" :scope="scopeFor(row.pane)">
                <component
                  :is="PANE_COMPONENTS[row.pane.kind]"
                  :pane="row.pane"
                  :scope="scopeFor(row.pane)"
                />
              </PaneFrame>
            </SplitterPanel>

            <SplitterPanel
              v-else-if="isLayoutRowTabs(row)"
              :default-size="row.size"
              :min-size="20"
              class="min-h-0"
            >
              <WorkspaceTabs :tabs="row.slot" :scope-for="scopeFor" />
            </SplitterPanel>
          </template>
        </SplitterGroup>
      </SplitterPanel>
    </template>
  </SplitterGroup>
</template>
