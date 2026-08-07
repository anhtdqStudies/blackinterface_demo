<script setup lang="ts">
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import { PANE_COMPONENTS, type Layout, type Pane } from './panes'
import PaneFrame from './PaneFrame.vue'
import type { ScopeRef } from '@/scope'

/**
 * Turns a `Layout` into a grid of panes. **It does not know what any pane
 * means** — it looks each kind up in `PANE_COMPONENTS` and hands over two props.
 *
 * That ignorance is the contract, and it is testable: there is no `v-if` on
 * `kind` in this file and `tools/check.py` fails the build if one appears. The
 * day adding a pane requires editing this component, adding a pane has stopped
 * being one line.
 *
 * Columns split horizontally, rows split vertically inside each column. Two
 * levels is all three presets need, and a general nested-split tree would be the
 * beginning of the layout editor ADR-0014 rejected outright.
 *
 * Drag-to-resize is remembered by `reka-ui` itself through `autoSaveId`, keyed
 * per preset. Deliberately not mirrored into the workspace store: pixel widths
 * would then have two owners, and the two would drift the first time somebody
 * resized the window mid-drag.
 */
const props = defineProps<{
  layout: Layout
  /** Namespaces the saved sizes. The preset name — sizes belong to a layout. */
  storageKey: string
  /** Where the workspace is pointed, for every pane that is not pinned. */
  scopeFor: (pane: Pane) => ScopeRef
}>()

const saveId = (suffix = ''): string => `bi.layout.${props.storageKey}${suffix}`
</script>

<template>
  <SplitterGroup
    direction="horizontal"
    :auto-save-id="saveId()"
    class="flex min-h-0 flex-1 bg-bg"
  >
    <template v-for="(col, ci) in layout.cols" :key="ci">
      <SplitterResizeHandle
        v-if="ci > 0"
        class="w-px shrink-0 bg-line transition-colors data-[state=drag]:bg-accent hover:bg-accent"
      />
      <SplitterPanel :default-size="col.size" :min-size="12" class="flex min-w-0 flex-col">
        <SplitterGroup
          direction="vertical"
          :auto-save-id="saveId(`.c${ci}`)"
          class="min-h-0 flex-1"
        >
          <template v-for="(row, ri) in col.rows" :key="row.pane.id">
            <SplitterResizeHandle
              v-if="ri > 0"
              class="h-px shrink-0 bg-line transition-colors data-[state=drag]:bg-accent hover:bg-accent"
            />
            <SplitterPanel :default-size="row.size" :min-size="10" class="min-h-0">
              <PaneFrame :pane="row.pane" :scope="scopeFor(row.pane)">
                <component
                  :is="PANE_COMPONENTS[row.pane.kind]"
                  :pane="row.pane"
                  :scope="scopeFor(row.pane)"
                />
              </PaneFrame>
            </SplitterPanel>
          </template>
        </SplitterGroup>
      </SplitterPanel>
    </template>
  </SplitterGroup>
</template>
