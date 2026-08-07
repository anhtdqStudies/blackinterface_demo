<script setup lang="ts">
/**
 * The frame everything signed-in lives inside: header, the one banner that has
 * to outrank whatever is on screen, and the route.
 *
 * It also owns the **data lifecycle** — one structure load, one stream — because
 * that has to happen once per session rather than once per pane. Panes come and
 * go every time somebody changes preset; the connection to the station must not.
 */
import { onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView } from 'vue-router'
import Header from './Header.vue'
import { ENG_PATH } from '@/router'
import { useSessionStore } from '@/stores/session'
import { useStreamStore } from '@/stores/stream'
import { useStructureStore } from '@/stores/structure'

const { t } = useI18n()
const structure = useStructureStore()
const stream = useStreamStore()
const session = useSessionStore()

/**
 * Nothing about the station is fetched until somebody is signed in.
 *
 * Not for secrecy — the API refuses those calls anyway — but because a login
 * screen that fires a stream and three failing requests behind itself fills the
 * console with 401s and makes a working login look broken.
 */
watch(
  () => session.authenticated,
  (signedIn) => {
    if (!signedIn) {
      stream.disconnect()
      return
    }
    void structure.load()
    void stream.prime()
    stream.connect()
  },
  { immediate: true },
)
onBeforeUnmount(() => stream.disconnect())
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- The shell chrome is for people who are signed in. The login screen brings
         its own layout: there is no station, no link and no identity to put in a
         header yet. -->
    <Header v-if="session.authenticated" />

    <p
      v-if="structure.error && session.authenticated"
      class="m-0 border-b border-st-closed bg-[color-mix(in_srgb,var(--color-st-closed)_18%,var(--color-bg))] px-4 py-2 text-sm"
    >
      <b>{{ structure.error.code }}</b> — {{ structure.error.message }}
      <template
        v-if="structure.error.code === 'model_not_loaded' && session.can('model.connect')"
      >
        · <RouterLink :to="ENG_PATH">{{ t('app.openOrCreateProject') }}</RouterLink>
      </template>
    </p>

    <RouterView />
  </div>
</template>
