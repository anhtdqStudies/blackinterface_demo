<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, Settings2 } from 'lucide-vue-next'
import AssistantPane from '@/features/engineer/AssistantPane.vue'
import ConnectionsPane from '@/features/engineer/ConnectionsPane.vue'
import CoveragePane from '@/features/engineer/CoveragePane.vue'
import ModelIssuesPane from '@/features/engineer/ModelIssuesPane.vue'
import { HOME_PATH } from '@/router'
import { useSessionStore } from '@/stores/session'
import { useStructureStore } from '@/stores/structure'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'

const { t } = useI18n()
const structure = useStructureStore()
const session = useSessionStore()
</script>

<template>
  <main class="relative flex-1 overflow-auto">
    <div
      class="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/6 via-background to-background"
      aria-hidden="true"
    />

    <div class="relative mx-auto max-w-3xl space-y-6 px-4 py-8">
      <header class="flex flex-wrap items-start gap-4">
        <div class="flex min-w-0 items-start gap-3">
          <span
            class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20"
          >
            <Settings2 class="size-5" />
          </span>
          <div class="min-w-0 space-y-1">
            <h1 class="m-0 text-2xl font-semibold tracking-tight text-foreground">
              {{ t('eng.title') }}
            </h1>
            <p v-if="structure.station" class="m-0 text-sm text-muted-foreground">
              {{ structure.station.name }}
              <Badge variant="secondary" class="ml-1.5 font-mono text-2xs font-normal">
                v{{ structure.station.model_version ?? '?' }}
              </Badge>
              <span class="mx-1 opacity-40">·</span>
              <span class="font-mono text-2xs">{{ structure.station.source }}</span>
            </p>
            <p v-else class="m-0 text-sm text-muted-foreground">{{ t('pane.noModel') }}</p>
          </div>
        </div>

        <RouterLink :to="HOME_PATH" class="ml-auto shrink-0">
          <Button variant="outline" size="sm" class="gap-1.5">
            <ArrowLeft class="size-3.5" />
            {{ t('eng.toOps') }}
          </Button>
        </RouterLink>
      </header>

      <ConnectionsPane />
      <AssistantPane v-if="session.can('assistant.config')" />
      <CoveragePane />
      <ModelIssuesPane />
    </div>
  </main>
</template>
