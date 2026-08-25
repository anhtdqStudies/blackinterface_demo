<script setup lang="ts">
/**
 * Vertical workspace navigation (replaces horizontal tab bar).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import { PANE_TITLE_KEY, type LayoutTabs, type PaneKind } from './panes'
import { workspaceNavIcon } from './workspace-nav'
import { useAlarmsStore } from '@/stores/alarms'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import { cn } from '@/lib/utils'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'

const props = defineProps<{
  tabs: LayoutTabs
}>()

const { t } = useI18n()
const workspace = useWorkspaceStore()
const structure = useStructureStore()
const alarms = useAlarmsStore()

const panes = computed(() => props.tabs.panes)

const anomalyCount = computed(() => structure.issues.filter((i) => i.group === 'C').length)

function badgeFor(kind: PaneKind): number | undefined {
  if (kind === 'anomalies' && anomalyCount.value > 0) return anomalyCount.value
  if (kind === 'alarms' && alarms.openBadge > 0) return alarms.openBadge
  return undefined
}

function onSelect(kind: PaneKind): void {
  workspace.setTab(kind)
  workspace.markTabPinnedByUser()
}

const navItemClass =
  'relative flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors hover:bg-muted/60'
</script>

<template>
  <TooltipProvider :delay-duration="400">
    <nav
      :class="
        cn(
          'flex shrink-0 flex-col border-r border-border bg-card/20',
          workspace.navCollapsed ? 'w-12' : 'w-44',
        )
      "
      :aria-label="t('workspace.nav')"
    >
      <div class="flex shrink-0 items-center justify-end border-b border-border/60 p-1.5">
        <Button
          variant="ghost"
          size="icon-xs"
          :title="
            workspace.navCollapsed ? t('workspace.navExpand') : t('workspace.navCollapse')
          "
          @click="workspace.toggleNavCollapsed()"
        >
          <PanelLeftOpen v-if="workspace.navCollapsed" class="size-3.5" />
          <PanelLeftClose v-else class="size-3.5" />
        </Button>
      </div>

      <div class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto p-1.5">
        <template v-for="p in panes" :key="p.id">
          <Tooltip v-if="workspace.navCollapsed" :disable-hoverable-content="true">
            <TooltipTrigger as-child>
              <button
                type="button"
                :class="
                  cn(navItemClass, 'justify-center px-0', {
                    'bg-muted text-foreground': workspace.tab === p.kind,
                    'text-muted-foreground': workspace.tab !== p.kind,
                  })
                "
                @click="onSelect(p.kind)"
              >
                <component :is="workspaceNavIcon(p.kind)" class="size-4 shrink-0" />
                <Badge
                  v-if="badgeFor(p.kind)"
                  variant="secondary"
                  class="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-1 text-2xs tabular-nums"
                >
                  {{ badgeFor(p.kind) }}
                </Badge>
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">{{ t(PANE_TITLE_KEY[p.kind]) }}</TooltipContent>
          </Tooltip>

          <button
            v-else
            type="button"
            :class="
              cn(navItemClass, {
                'bg-muted text-foreground': workspace.tab === p.kind,
                'text-muted-foreground': workspace.tab !== p.kind,
              })
            "
            @click="onSelect(p.kind)"
          >
            <component :is="workspaceNavIcon(p.kind)" class="size-4 shrink-0 opacity-80" />
            <span class="min-w-0 flex-1 truncate">{{ t(PANE_TITLE_KEY[p.kind]) }}</span>
            <Badge
              v-if="badgeFor(p.kind)"
              variant="secondary"
              class="h-4 min-w-4 shrink-0 bg-primary/15 px-1 text-2xs tabular-nums text-primary"
            >
              {{ badgeFor(p.kind) }}
            </Badge>
          </button>
        </template>
      </div>
    </nav>
  </TooltipProvider>
</template>
