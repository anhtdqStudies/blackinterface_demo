<script setup lang="ts">
/**
 * Workspace column — vertical nav + scope header + pane (+ optional details rail on SLD).
 */
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import ScopeHeader from '@/features/monitoring/ScopeHeader.vue'
import WorkspaceDetails from './WorkspaceDetails.vue'
import WorkspaceNav from './WorkspaceNav.vue'
import { PANE_COMPONENTS, type LayoutTabs, type Pane, type PaneKind } from './panes'
import type { ScopeRef } from '@/scope'
import { useAlarmsStore } from '@/stores/alarms'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<{
  tabs: LayoutTabs
  scopeFor: (pane: Pane) => ScopeRef
}>()

const { t } = useI18n()
const workspace = useWorkspaceStore()
const alarms = useAlarmsStore()

onMounted(() => {
  alarms.followIncidents()
})

const panes = computed(() => props.tabs.panes)

const activePane = computed(
  () => panes.value.find((p) => p.kind === workspace.tab) ?? panes.value[0],
)

const activeScope = computed(() =>
  activePane.value ? props.scopeFor(activePane.value) : props.scopeFor(panes.value[0]!),
)

const detailsEligible = computed(
  () =>
    workspace.tab === 'sld' &&
    (activeScope.value.kind === 'bay' || activeScope.value.kind === 'device') &&
    !workspace.detailsDismissed,
)

function panePadding(kind: PaneKind): string {
  return kind === 'sld' ? 'p-0' : 'p-4'
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col bg-background">
    <ScopeHeader :scope="activeScope" />

    <div class="flex min-h-0 flex-1">
      <WorkspaceNav :tabs="tabs" />

      <SplitterGroup
        v-if="detailsEligible"
        direction="horizontal"
        auto-save-id="bi.layout.ops.details"
        class="min-h-0 min-w-0 flex-1"
      >
        <SplitterPanel :default-size="72" :min-size="40" class="min-h-0 min-w-0">
          <div
            v-if="activePane"
            class="h-full min-h-0 overflow-auto"
            :class="panePadding(activePane.kind)"
          >
            <component
              :is="PANE_COMPONENTS[activePane.kind]"
              :pane="activePane"
              :scope="scopeFor(activePane)"
              class="h-full min-h-0"
            />
          </div>
        </SplitterPanel>

        <SplitterResizeHandle
          class="w-px shrink-0 bg-border transition-colors data-[state=drag]:bg-primary/60 hover:bg-primary/40"
        />

        <SplitterPanel
          :default-size="28"
          :min-size="18"
          :max-size="40"
          collapsible
          :collapsed-size="0"
          class="min-h-0"
        >
          <WorkspaceDetails :scope="activeScope" />
        </SplitterPanel>
      </SplitterGroup>

      <div v-else class="min-h-0 min-w-0 flex-1 overflow-hidden">
        <div
          v-if="activePane"
          class="h-full min-h-0 overflow-auto"
          :class="panePadding(activePane.kind)"
        >
          <component
            :is="PANE_COMPONENTS[activePane.kind]"
            :pane="activePane"
            :scope="scopeFor(activePane)"
            class="h-full min-h-0"
          />
        </div>
      </div>
    </div>

    <p
      v-if="
        workspace.tab === 'sld' &&
        (activeScope.kind === 'bay' || activeScope.kind === 'device') &&
        workspace.detailsDismissed
      "
      class="shrink-0 border-t border-border/60 px-4 py-1.5 text-center text-2xs text-muted-foreground"
    >
      <button
        type="button"
        class="text-primary underline-offset-2 hover:underline"
        @click="workspace.reopenDetails()"
      >
        {{ t('workspace.detailsReopen') }}
      </button>
    </p>
  </div>
</template>
