<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Empty from '@/ui/Empty.vue'

/**
 * A pane whose component has not been built yet.
 *
 * It exists so a preset can name a pane before the pane exists — `chat` is in
 * the shipped layouts from GD 1.5, and GD 2 replaces one line of
 * `PANE_COMPONENTS` without touching the layout contract. The alternative,
 * leaving the kind out of the presets until its component lands, means editing
 * the presets later, which is editing the thing the contract froze.
 *
 * It says so plainly rather than showing a blank cell: an operator must be able
 * to tell "not built yet" from "broken right now".
 */
const { t } = useI18n()
</script>

<template>
  <Empty :reason="t('pane.later')" />
</template>
