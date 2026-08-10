<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AssistantPane from '@/features/engineer/AssistantPane.vue'
import ConnectionsPane from '@/features/engineer/ConnectionsPane.vue'
import CoveragePane from '@/features/engineer/CoveragePane.vue'
import ModelIssuesPane from '@/features/engineer/ModelIssuesPane.vue'
import { HOME_PATH } from '@/router'
import { useSessionStore } from '@/stores/session'
import { useStructureStore } from '@/stores/structure'
import { Button } from '@/ui/button'
import { Separator } from '@/ui/separator'

const { t } = useI18n()
const structure = useStructureStore()
const session = useSessionStore()
</script>

<template>
  <main class="mx-auto flex max-w-[960px] flex-1 flex-col gap-0 overflow-auto bg-background">
    <div
      class="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-border bg-background px-4 py-3"
    >
      <h1 class="m-0 text-base font-semibold text-foreground">
        {{ t('eng.title') }}
        <span v-if="structure.station" class="font-normal text-muted-foreground">
          · {{ structure.station.name }}
        </span>
      </h1>
      <span v-if="structure.station" class="text-xs text-muted-foreground">
        ModelVersion
        <b class="text-foreground">{{ structure.station.model_version ?? '?' }}</b>
        · {{ structure.station.source }}
      </span>
      <RouterLink :to="HOME_PATH" class="ml-auto">
        <Button variant="default" size="xs">{{ t('eng.toOps') }} ▸</Button>
      </RouterLink>
    </div>

    <ConnectionsPane />
    <Separator />
    <AssistantPane v-if="session.can('assistant.config')" />
    <Separator v-if="session.can('assistant.config')" />
    <CoveragePane />
    <Separator />
    <ModelIssuesPane />
  </main>
</template>
