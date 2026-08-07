<script setup lang="ts">
/**
 * Engineer surface — one screen, not a workflow (screens.md §3.4, ADR-0014 §10 lô 3).
 *
 * Connections · coverage · model issues (A+B). Group C is on the operator
 * `anomalies` pane instead.
 */
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ConnectionsPane from '@/features/engineer/ConnectionsPane.vue'
import CoveragePane from '@/features/engineer/CoveragePane.vue'
import ModelIssuesPane from '@/features/engineer/ModelIssuesPane.vue'
import { HOME_PATH } from '@/router'
import { useStructureStore } from '@/stores/structure'

const { t } = useI18n()
const structure = useStructureStore()
</script>

<template>
  <main class="mx-auto flex max-w-[960px] flex-1 flex-col gap-0 overflow-auto">
    <div
      class="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-line bg-bg px-4 py-3"
    >
      <h1 class="m-0 text-base font-semibold">
        {{ t('eng.title') }}
        <span v-if="structure.station" class="font-normal text-dim">
          · {{ structure.station.name }}
        </span>
      </h1>
      <span v-if="structure.station" class="text-xs text-dim">
        ModelVersion
        <b class="text-fg">{{ structure.station.model_version ?? '?' }}</b>
        · {{ structure.station.source }}
      </span>
      <RouterLink :to="HOME_PATH" class="on ml-auto text-xs no-underline">
        {{ t('eng.toOps') }} ▸
      </RouterLink>
    </div>

    <ConnectionsPane />
    <CoveragePane />
    <ModelIssuesPane />
  </main>
</template>
