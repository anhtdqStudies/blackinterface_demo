<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView } from 'vue-router'
import Header from './Header.vue'
import { ENG_PATH } from '@/router'
import { useSessionStore } from '@/stores/session'
import { useStreamStore } from '@/stores/stream'
import { useStructureStore } from '@/stores/structure'
import { Alert, AlertDescription, AlertTitle } from '@/ui/alert'

const { t } = useI18n()
const structure = useStructureStore()
const stream = useStreamStore()
const session = useSessionStore()

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
    <Header v-if="session.authenticated" />

    <Alert
      v-if="structure.error && session.authenticated"
      variant="destructive"
      class="rounded-none border-x-0 border-t-0"
    >
      <AlertTitle>{{ structure.error.code }}</AlertTitle>
      <AlertDescription>
        {{ structure.error.message }}
        <template
          v-if="structure.error.code === 'model_not_loaded' && session.can('model.connect')"
        >
          · <RouterLink :to="ENG_PATH">{{ t('app.openOrCreateProject') }}</RouterLink>
        </template>
      </AlertDescription>
    </Alert>

    <RouterView />
  </div>
</template>
