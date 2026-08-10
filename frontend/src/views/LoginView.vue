<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
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
  <div class="flex min-h-full items-center justify-center p-6">
    <Card class="w-full max-w-sm">
      <CardHeader>
        <CardTitle class="text-lg">{{ t('app.brand') }}</CardTitle>
        <CardDescription>{{ t('login.subtitle') }}</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="flex flex-col gap-4" @submit.prevent="submit">
          <div class="flex flex-col gap-1.5">
            <Label for="username">{{ t('login.username') }}</Label>
            <Input
              id="username"
              v-model="username"
              autocomplete="username"
              autofocus
              required
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <Label for="password">{{ t('login.password') }}</Label>
            <Input
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
            />
          </div>

          <Alert v-if="error" variant="destructive">
            <AlertDescription>{{ error }}</AlertDescription>
          </Alert>

          <Button type="submit" class="w-full" :disabled="busy">
            {{ busy ? t('login.signingIn') : t('login.signIn') }}
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
