<script setup lang="ts">
/**
 * Station name · link health · which layout · who you are · language.
 *
 * Two rows on the workspace: identity + link on top; preset picker + metadata below.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { PRESET_LABEL_KEY, PRESET_NAMES, type PresetName } from './presets'
import { setLocale, SUPPORTED, type Locale } from '@/i18n'
import { ENG_PATH, HOME_PATH, LOGIN_PATH } from '@/router'
import { useLiveStore } from '@/stores/live'
import { useSessionStore } from '@/stores/session'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import StatusDot, { type SystemStatus } from '@/ui/StatusDot.vue'

const { t, locale } = useI18n()
const structure = useStructureStore()
const live = useLiveStore()
const session = useSessionStore()
const workspace = useWorkspaceStore()
const route = useRoute()
const router = useRouter()

const onWorkspace = computed(() => route.name === 'ops')
const onEng = computed(() => route.name === 'eng')

function pick(name: PresetName): void {
  workspace.setPreset(name)
}

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
  <header class="border-b border-line bg-panel">
    <!-- Row 1: who we are, link health, account -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
      <RouterLink
        :to="HOME_PATH"
        class="text-lg font-semibold tracking-[0.02em] text-fg no-underline"
      >
        {{ t('app.brand') }}
      </RouterLink>

      <span v-if="structure.station" class="text-sm font-semibold text-fg">
        {{ structure.station.name }}
      </span>
      <span v-else-if="structure.loading" class="text-sm text-dim">{{ t('app.loading') }}</span>

      <StatusDot :status="status" :label="statusLabel" :title="statusTitle" />

      <nav class="ml-auto flex flex-wrap items-center gap-[14px]">
        <RouterLink
          v-if="!onEng"
          :to="HOME_PATH"
          class="text-sm text-dim no-underline hover:text-fg"
        >
          {{ t('nav.diagram') }}
        </RouterLink>
        <RouterLink
          v-if="session.can('model.connect')"
          :to="ENG_PATH"
          class="text-sm text-dim no-underline hover:text-fg"
        >
          {{ t('nav.engineering') }}
        </RouterLink>

        <span
          class="text-xs text-dim"
          :title="`${session.user} · ${session.capabilities.size} ${t('session.capabilities')}`"
        >
          {{ session.displayName }}
          <b class="font-semibold text-fg">{{ session.roles.join(' + ') }}</b>
        </span>

        <button
          v-if="session.authMode === 'session'"
          class="text-xs"
          :title="t('session.signOut')"
          @click="signOut"
        >
          {{ t('session.signOut') }}
        </button>

        <select
          :value="locale"
          :aria-label="t('nav.language')"
          class="rounded-[var(--radius)] border border-line bg-panel-2 px-[6px] py-[3px] text-xs text-dim"
          @change="switchLocale(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="code in SUPPORTED" :key="code" :value="code">
            {{ code.toUpperCase() }}
          </option>
        </select>

        <button
          v-if="session.can('model.connect')"
          class="text-xs"
          :disabled="structure.reloading"
          @click="structure.reload()"
        >
          {{ structure.reloading ? t('app.reloading') : t('app.reloadSource') }}
        </button>
      </nav>
    </div>

    <!-- Row 2: preset (workspace only) + technical metadata -->
    <div
      v-if="onWorkspace"
      class="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-1.5"
    >
      <div class="segmented" role="group" :aria-label="t('preset.label')">
        <button
          v-for="name in PRESET_NAMES"
          :key="name"
          type="button"
          class="segmented-btn"
          :class="{ active: name === workspace.preset }"
          :aria-pressed="name === workspace.preset"
          @click="pick(name)"
        >
          {{ t(PRESET_LABEL_KEY[name]) }}
        </button>
      </div>
      <span v-if="metaLine" class="text-2xs text-dim">{{ metaLine }}</span>
    </div>
  </header>
</template>

<style scoped>
nav a.router-link-active {
  color: var(--color-fg);
}

.segmented {
  display: inline-flex;
  border: 1px solid var(--color-line);
  border-radius: var(--radius);
  overflow: hidden;
}

.segmented-btn {
  border: none;
  border-radius: 0;
  padding: 4px 12px;
  font-size: 11px;
  background: var(--color-panel-2);
  color: var(--color-dim);
}

.segmented-btn + .segmented-btn {
  border-left: 1px solid var(--color-line);
}

.segmented-btn:hover:not(.active) {
  color: var(--color-fg);
  border-color: transparent;
}

.segmented-btn.active {
  background: var(--color-accent);
  color: #08111f;
  font-weight: 600;
}
</style>
