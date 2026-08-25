<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { LogIn, Zap } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { landingFor } from '@/router'
import { useSessionStore } from '@/stores/session'
import { Alert, AlertDescription } from '@/ui/alert'
import { Button } from '@/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/ui/card'
import { Input } from '@/ui/input'
import { Label } from '@/ui/label'

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
  <div class="relative flex min-h-full flex-col items-center justify-center px-4 py-10">
    <div
      class="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/8 via-background to-background"
      aria-hidden="true"
    />

    <div class="relative w-full max-w-md space-y-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <span
          class="flex size-12 items-center justify-center rounded-2xl bg-primary/15 text-primary shadow-sm ring-1 ring-primary/20"
        >
          <Zap class="size-6" />
        </span>
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold tracking-tight text-foreground">
            {{ t('app.brand') }}
          </h1>
          <p class="text-sm text-muted-foreground">{{ t('login.subtitle') }}</p>
        </div>
      </div>

      <Card class="rounded-2xl border-border/70 shadow-lg">
        <CardHeader class="sr-only">
          <CardTitle>{{ t('login.signIn') }}</CardTitle>
          <CardDescription>{{ t('login.subtitle') }}</CardDescription>
        </CardHeader>
        <CardContent class="pt-6">
          <form class="flex flex-col gap-5" @submit.prevent="submit">
            <div class="flex flex-col gap-2">
              <Label for="username">{{ t('login.username') }}</Label>
              <Input
                id="username"
                v-model="username"
                autocomplete="username"
                autofocus
                required
                class="h-10"
              />
            </div>

            <div class="flex flex-col gap-2">
              <Label for="password">{{ t('login.password') }}</Label>
              <Input
                id="password"
                v-model="password"
                type="password"
                autocomplete="current-password"
                required
                class="h-10"
              />
            </div>

            <Alert v-if="error" variant="destructive">
              <AlertDescription>{{ error }}</AlertDescription>
            </Alert>

            <Button type="submit" class="h-10 w-full gap-2" :disabled="busy">
              <LogIn class="size-4" />
              {{ busy ? t('login.signingIn') : t('login.signIn') }}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
