<script setup lang="ts">
/**
 * Tabbed workspace column (ADR-0018) — SLD and monitoring panes share one bar.
 *
 * Renders panes through PANE_COMPONENTS only; no branch on `kind` beyond the
 * register lookup that `PaneHost` already uses for single panes.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ScopeHeader from '@/features/monitoring/ScopeHeader.vue'
import {
  PANE_COMPONENTS,
  PANE_TITLE_KEY,
  type LayoutTabs,
  type Pane,
  type PaneKind,
} from './panes'
import type { ScopeRef } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import { Badge } from '@/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui/tabs'

const props = defineProps<{
  tabs: LayoutTabs
  scopeFor: (pane: Pane) => ScopeRef
}>()

const { t } = useI18n()
const workspace = useWorkspaceStore()
const structure = useStructureStore()

const panes = computed(() => props.tabs.panes)

const anomalyCount = computed(() => structure.issues.filter((i) => i.group === 'C').length)

const activeScope = computed(() => props.scopeFor(panes.value[0] ?? { id: 'sld', kind: 'sld' }))

function badgeFor(kind: PaneKind): number | undefined {
  if (kind === 'anomalies' && anomalyCount.value > 0) return anomalyCount.value
  return undefined
}

function onTabChange(value: string | number): void {
  workspace.setTab(String(value) as PaneKind)
  workspace.markTabPinnedByUser()
}

function panePadding(kind: PaneKind): string {
  return kind === 'sld' ? 'p-0' : 'p-3'
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col bg-card">
    <ScopeHeader :scope="activeScope" />

    <Tabs
      :model-value="workspace.tab"
      class="flex min-h-0 flex-1 flex-col gap-0"
      @update:model-value="onTabChange"
    >
      <TabsList
        variant="line"
        class="h-9 w-full shrink-0 justify-start rounded-none border-b border-border bg-transparent px-2"
      >
        <TabsTrigger
          v-for="p in panes"
          :key="p.id"
          :value="p.kind"
          class="gap-1.5 px-3 text-xs data-[state=active]:bg-muted"
        >
          {{ t(PANE_TITLE_KEY[p.kind]) }}
          <Badge
            v-if="badgeFor(p.kind)"
            variant="destructive"
            class="h-4 min-w-4 px-1 text-2xs tabular-nums"
          >
            {{ badgeFor(p.kind) }}
          </Badge>
        </TabsTrigger>
      </TabsList>

      <TabsContent
        v-for="p in panes"
        :key="p.id"
        :value="p.kind"
        class="mt-0 min-h-0 flex-1 overflow-auto data-[state=inactive]:hidden"
        :class="panePadding(p.kind)"
      >
        <component
          :is="PANE_COMPONENTS[p.kind]"
          :pane="p"
          :scope="scopeFor(p)"
          class="h-full min-h-0"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>
