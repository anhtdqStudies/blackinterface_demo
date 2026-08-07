<script setup lang="ts">
/**
 * The operations workspace. All of it: pick a layout, hand it to `PaneHost`.
 *
 * This replaces `StationView`, which hard-coded one arrangement — diagram left,
 * sidebar right — in its template. That arrangement is now `presets.monitor`,
 * one object among three, and adding a fourth is a data change.
 *
 * There is no local selection state here and there must never be. What every
 * pane describes is `workspace.scope`, which is the URL (ADR-0010) — so the
 * screen can be linked to, reloaded into, and later handed to the agent as "what
 * I am looking at". The version before this kept `selectedBay` and
 * `selectedDevice` as refs and had to clear them by hand in three places.
 */
import PaneHost from '@/app/layout/PaneHost.vue'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
</script>

<template>
  <PaneHost
    :layout="workspace.layout"
    :storage-key="workspace.preset"
    :scope-for="workspace.scopeOf"
  />
</template>
