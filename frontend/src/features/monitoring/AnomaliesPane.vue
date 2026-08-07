<script setup lang="ts">
/**
 * Runtime anomalies (group C) on the operator surface (GĐ 1.5 lô 3).
 *
 * The backend classifies issues into A/B/C; this pane shows only C — things
 * that matter while the station is running, not while the model is being built.
 *
 * **Always the whole station, never narrowed to the pane's scope** (user's call,
 * 2026-08-07). Every other pane answers *about the thing you clicked*; this one
 * answers *what is wrong anywhere*, and those are different questions. An
 * earthing switch closed on a live section in D12 does not stop being urgent
 * because somebody is currently looking at E07 — filtering it away would hide
 * exactly the case the pane exists for.
 *
 * The price is that this cell disagrees with its neighbours about what is on
 * screen, so it has to **say so** whenever the workspace is aimed somewhere
 * narrower. Same rule as a pinned pane: a cell that does not follow the screen
 * announces it, or it becomes a trap.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PaneProps } from '@/app/layout/panes'
import IssueList from '@/features/shared/IssueList.vue'
import { formatScope } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import Empty from '@/ui/Empty.vue'
import Skeleton from '@/ui/Skeleton.vue'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const structure = useStructureStore()

const anomalies = computed(() => structure.issues.filter((i) => i.group === 'C'))

/** The scope being ignored, or null when there is nothing to disclose. */
const ignoring = computed(() =>
  props.scope.kind === 'station' ? null : formatScope(props.scope),
)
</script>

<template>
  <div class="p-3">
    <p v-if="ignoring" class="mb-2 text-2xs text-dim">
      {{ t('anomalies.stationWide', { scope: ignoring }) }}
    </p>
    <Skeleton v-if="structure.loading" variant="row" :count="3" />
    <IssueList v-else-if="structure.station" :issues="anomalies" :empty="t('anomalies.none')" />
    <Empty v-else :reason="t('pane.noModel')" />
  </div>
</template>
