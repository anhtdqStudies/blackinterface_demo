<script setup lang="ts">
/**
 * Signing in (ADR-0017).
 *
 * The only screen that renders outside the application shell, because there is
 * nothing yet to put in a header: no station, no link, no identity.
 *
 * One message for every failure, matching the backend. Saying "no such account"
 * would tell whoever is guessing which usernames exist — and at an unattended
 * station this page is reachable over the network.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { landingFor } from '@/router'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const username = ref('')
const password = ref('')
const error = ref<string | null>(null)
const busy = ref(false)

async function submit(): Promise<void> {
  busy.value = true
  error.value = null
  try {
    await session.signIn(username.value, password.value)
    // Back to whatever was asked for before the redirect, else the landing for
    // these roles. `redirect` is a path from our own router, never a full URL:
    // an open redirect on a login page is how a phishing link gets its polish.
    const wanted = route.query.redirect
    const to =
      typeof wanted === 'string' && wanted.startsWith('/') ? wanted : landingFor(session.roles)
    await router.replace(to)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
    password.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex min-h-full items-center justify-center p-6">
    <form
      class="w-full max-w-sm rounded-[var(--radius)] border border-line bg-panel p-6"
      @submit.prevent="submit"
    >
      <h1 class="m-0 text-lg font-semibold tracking-[0.02em] text-fg">
        {{ t('app.brand') }}
      </h1>
      <p class="mt-1 mb-5 text-sm text-dim">{{ t('login.subtitle') }}</p>

      <label class="mb-1 block text-xs text-dim" for="username">
        {{ t('login.username') }}
      </label>
      <input
        id="username"
        v-model="username"
        autocomplete="username"
        autofocus
        required
        class="mb-4 w-full rounded-[var(--radius)] border border-line bg-panel-2 px-3 py-2 text-sm text-fg"
      />

      <label class="mb-1 block text-xs text-dim" for="password">
        {{ t('login.password') }}
      </label>
      <input
        id="password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        required
        class="mb-4 w-full rounded-[var(--radius)] border border-line bg-panel-2 px-3 py-2 text-sm text-fg"
      />

      <!-- role="alert" so a screen reader announces the refusal; a colour
           change alone would say nothing to anyone who cannot see it. -->
      <p
        v-if="error"
        role="alert"
        class="mt-0 mb-4 rounded-[var(--radius)] border border-st-closed bg-[color-mix(in_srgb,var(--color-st-closed)_18%,var(--color-bg))] px-3 py-2 text-sm"
      >
        {{ error }}
      </p>

      <button type="submit" :disabled="busy" class="w-full">
        {{ busy ? t('login.signingIn') : t('login.signIn') }}
      </button>
    </form>
  </div>
</template>
