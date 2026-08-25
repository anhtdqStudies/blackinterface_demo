<script setup lang="ts">
/**
 * The operations workspace. All of it: one layout, hand it to `PaneHost`.
 *
 * There is no local selection state here and there must never be. What every
 * pane describes is `workspace.scope`, which is the URL (ADR-0010).
 */
import PaneHost from '@/app/layout/PaneHost.vue'
import { OPERATOR_LAYOUT } from '@/app/layout/presets'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
</script>

<template>
  <PaneHost :layout="OPERATOR_LAYOUT" storage-key="ops" :scope-for="workspace.scopeOf" />
</template>
