<script setup lang="ts">
/**
 * Station name · link health · who you are · language.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RefreshCw, Zap } from 'lucide-vue-next'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { setLocale, SUPPORTED, type Locale } from '@/i18n'
import { cn } from '@/lib/utils'
import { ENG_PATH, HOME_PATH, LOGIN_PATH } from '@/router'
import { useLiveStore } from '@/stores/live'
import { useSessionStore } from '@/stores/session'
import { useStructureStore } from '@/stores/structure'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'
import { Separator } from '@/ui/separator'
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

function switchLocale(next: unknown): void {
  if (typeof next === 'string') setLocale(next as Locale)
}

async function signOut(): Promise<void> {
  await session.signOut()
  await router.push(LOGIN_PATH)
}

const navLinkClass =
  'rounded-md px-2.5 py-1.5 text-sm text-muted-foreground no-underline transition-colors hover:bg-muted hover:text-foreground'
</script>

<template>
  <header class="border-b border-border bg-background">
    <div class="flex h-14 items-center gap-3 px-4">
      <!-- Brand + station -->
      <div class="flex min-w-0 items-center gap-2.5">
        <RouterLink
          :to="HOME_PATH"
          class="flex shrink-0 items-center gap-2 text-foreground no-underline"
        >
          <span
            class="flex size-7 items-center justify-center rounded-lg bg-primary/15 text-primary"
          >
            <Zap class="size-3.5" />
          </span>
          <span class="hidden text-sm font-semibold tracking-tight sm:inline">
            {{ t('app.brand') }}
          </span>
        </RouterLink>

        <Separator orientation="vertical" class="hidden h-5 sm:block" />

        <Badge
          v-if="structure.station"
          variant="secondary"
          class="max-w-[10rem] truncate font-normal sm:max-w-xs"
        >
          {{ structure.station.name }}
        </Badge>
        <span v-else-if="structure.loading" class="text-sm text-muted-foreground">
          {{ t('app.loading') }}
        </span>
      </div>

      <!-- Link status + meta -->
      <div class="hidden min-w-0 items-center gap-3 md:flex">
        <span
          class="inline-flex items-center rounded-full border border-border/60 bg-muted/40 px-2.5 py-1"
        >
          <StatusDot :status="status" :label="statusLabel" :title="statusTitle" />
        </span>
        <span v-if="metaLine" class="truncate text-xs text-muted-foreground" :title="metaLine">
          {{ metaLine }}
        </span>
      </div>

      <!-- Actions -->
      <nav class="ml-auto flex shrink-0 items-center gap-1.5">
        <RouterLink
          v-if="!onEng"
          :to="HOME_PATH"
          :class="cn(navLinkClass, { 'bg-muted text-foreground': route.name === 'ops' })"
        >
          {{ t('nav.diagram') }}
        </RouterLink>
        <RouterLink
          v-if="session.can('model.connect')"
          :to="ENG_PATH"
          :class="cn(navLinkClass, { 'bg-muted text-foreground': onEng })"
        >
          {{ t('nav.engineering') }}
        </RouterLink>

        <Separator orientation="vertical" class="mx-1 hidden h-5 sm:block" />

        <span
          class="hidden max-w-[8rem] truncate text-xs text-muted-foreground lg:inline"
          :title="`${session.user} · ${session.capabilities.size} ${t('session.capabilities')}`"
        >
          {{ session.displayName }}
          <span class="font-medium text-foreground">{{ session.roles.join(' + ') }}</span>
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

        <Select :model-value="locale" @update:model-value="switchLocale">
          <SelectTrigger class="h-8 w-[4.25rem] text-xs" :aria-label="t('nav.language')">
            <SelectValue />
          </SelectTrigger>
          <SelectContent align="end">
            <SelectItem v-for="code in SUPPORTED" :key="code" :value="code">
              {{ code.toUpperCase() }}
            </SelectItem>
          </SelectContent>
        </Select>

        <Button
          v-if="session.can('model.connect')"
          variant="outline"
          size="icon-xs"
          :disabled="structure.reloading"
          :title="structure.reloading ? t('app.reloading') : t('app.reloadSource')"
          @click="structure.reload()"
        >
          <RefreshCw :class="structure.reloading ? 'animate-spin' : ''" />
        </Button>
      </nav>
    </div>

    <!-- Mobile meta row -->
    <div
      v-if="metaLine"
      class="flex items-center gap-2 border-t border-border/50 px-4 py-1.5 md:hidden"
    >
      <StatusDot :status="status" :label="statusLabel" :title="statusTitle" />
      <span class="truncate text-2xs text-muted-foreground">{{ metaLine }}</span>
    </div>
  </header>
</template>
