<script setup lang="ts">
/**
 * Station name · link health · who you are · language.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { setLocale, SUPPORTED, type Locale } from '@/i18n'
import { ENG_PATH, HOME_PATH, LOGIN_PATH } from '@/router'
import { useLiveStore } from '@/stores/live'
import { useSessionStore } from '@/stores/session'
import { useStructureStore } from '@/stores/structure'
import { Button } from '@/ui/button'
import StatusDot, { type SystemStatus } from '@/ui/StatusDot.vue'

const { t, locale } = useI18n()
const structure = useStructureStore()
const live = useLiveStore()
const session = useSessionStore()
const route = useRoute()
const router = useRouter()

const onEng = computed(() => route.name === 'eng')

const status = computed<SystemStatus>(() => {
  const link = live.link
  if (!link || !link.realtime) return 'idle'
  if (!link.connected) return 'down'
  return link.rejected ? 'warn' : 'ok'
})

const statusLabel = computed(
  () =>
    ({
      ok: t('link.online'),
      warn: t('link.onlinePartial'),
      down: t('link.offline'),
      idle: t('link.snapshot'),
    })[status.value],
)

const statusTitle = computed(() => {
  const link = live.link
  if (!link || !link.realtime) return t('link.snapshotHint')
  if (!link.connected) {
    return link.error ? t('link.offlineHintWhy', { error: link.error }) : t('link.offlineHint')
  }
  return link.rejected
    ? t('link.watchingRejected', { count: link.watching, rejected: link.rejected })
    : t('link.watching', { count: link.watching })
})

const metaLine = computed(() => {
  const st = structure.station
  if (!st) return null
  return t('header.meta', {
    version: st.model_version ?? '?',
    bays: st.bay_count,
    devices: st.device_count,
    source: st.source,
  })
})

function switchLocale(next: string): void {
  setLocale(next as Locale)
}

async function signOut(): Promise<void> {
  await session.signOut()
  await router.push(LOGIN_PATH)
}
</script>

<template>
  <header class="border-b border-border bg-background">
    <div class="flex h-14 flex-wrap items-center gap-x-4 gap-y-2 px-4">
      <RouterLink
        :to="HOME_PATH"
        class="text-lg font-semibold tracking-tight text-foreground no-underline"
      >
        {{ t('app.brand') }}
      </RouterLink>

      <span v-if="structure.station" class="text-sm font-semibold text-foreground">
        {{ structure.station.name }}
      </span>
      <span v-else-if="structure.loading" class="text-sm text-muted-foreground">
        {{ t('app.loading') }}
      </span>

      <StatusDot :status="status" :label="statusLabel" :title="statusTitle" />

      <span v-if="metaLine" class="hidden text-xs text-muted-foreground lg:inline">
        {{ metaLine }}
      </span>

      <nav class="ml-auto flex flex-wrap items-center gap-2">
        <RouterLink
          v-if="!onEng"
          :to="HOME_PATH"
          class="text-sm text-muted-foreground no-underline hover:text-foreground"
        >
          {{ t('nav.diagram') }}
        </RouterLink>
        <RouterLink
          v-if="session.can('model.connect')"
          :to="ENG_PATH"
          class="text-sm text-muted-foreground no-underline hover:text-foreground"
        >
          {{ t('nav.engineering') }}
        </RouterLink>

        <span
          class="text-xs text-muted-foreground"
          :title="`${session.user} · ${session.capabilities.size} ${t('session.capabilities')}`"
        >
          {{ session.displayName }}
          <b class="font-semibold text-foreground">{{ session.roles.join(' + ') }}</b>
        </span>

        <Button
          v-if="session.authMode === 'session'"
          variant="ghost"
          size="xs"
          :title="t('session.signOut')"
          @click="signOut"
        >
          {{ t('session.signOut') }}
        </Button>

        <select
          :value="locale"
          :aria-label="t('nav.language')"
          class="h-8 rounded-md border border-input bg-muted px-2 text-xs text-muted-foreground"
          @change="switchLocale(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="code in SUPPORTED" :key="code" :value="code">
            {{ code.toUpperCase() }}
          </option>
        </select>

        <Button
          v-if="session.can('model.connect')"
          variant="outline"
          size="xs"
          :disabled="structure.reloading"
          @click="structure.reload()"
        >
          {{ structure.reloading ? t('app.reloading') : t('app.reloadSource') }}
        </Button>
      </nav>
    </div>
  </header>
</template>

<style scoped>
nav a.router-link-active {
  color: var(--foreground);
}
</style>
