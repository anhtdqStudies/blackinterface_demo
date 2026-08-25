<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bot, KeyRound, Zap } from 'lucide-vue-next'
import { ApiError, api, type AssistantConfig, type AssistantProbe } from '@/api/client'
import SysBadge from '@/ui/SysBadge.vue'
import { Alert, AlertDescription } from '@/ui/alert'
import ErrorBox from '@/ui/ErrorBox.vue'
import Field from '@/ui/Field.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Button } from '@/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/ui/card'
import { Input } from '@/ui/input'
import { Label } from '@/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'
import { Separator } from '@/ui/separator'

const { t, locale } = useI18n()

const config = ref<AssistantConfig | null>(null)
const loading = ref(true)
const error = ref<ApiError | null>(null)

const provider = ref<'off' | 'openai'>('off')
const baseUrl = ref('')
const model = ref('')
const apiKey = ref('')
const saving = ref(false)
const testing = ref(false)
const probe = ref<AssistantProbe | null>(null)

function adopt(next: AssistantConfig): void {
  config.value = next
  provider.value = next.provider === 'openai' ? 'openai' : 'off'
  baseUrl.value = next.base_url
  model.value = next.model
  apiKey.value = ''
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    adopt(await api.assistant())
  } catch (cause) {
    error.value = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  saving.value = true
  error.value = null
  probe.value = null
  try {
    adopt(
      await api.saveAssistant({
        provider: provider.value,
        base_url: baseUrl.value,
        model: model.value,
        timeout: config.value?.timeout ?? 120,
        api_key: apiKey.value ? apiKey.value : undefined,
      }),
    )
  } catch (cause) {
    error.value = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
  } finally {
    saving.value = false
  }
}

async function clearKey(): Promise<void> {
  if (!window.confirm(t('assistant.confirmClearKey'))) return
  saving.value = true
  try {
    adopt(
      await api.saveAssistant({
        provider: provider.value,
        base_url: baseUrl.value,
        model: model.value,
        timeout: config.value?.timeout ?? 120,
        api_key: '',
      }),
    )
  } finally {
    saving.value = false
  }
}

async function test(): Promise<void> {
  testing.value = true
  probe.value = null
  try {
    probe.value = await api.testAssistant()
    if (probe.value.ok) adopt(await api.assistant())
  } catch (cause) {
    error.value = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
  } finally {
    testing.value = false
  }
}

function when(iso: string | null | undefined): string {
  if (!iso) return t('common.dash')
  const at = new Date(iso)
  return isNaN(at.getTime()) ? iso : at.toLocaleString(locale.value)
}

onMounted(() => void load())
</script>

<template>
  <PaneSkeleton v-if="loading" variant="row" :count="3" />
  <ErrorBox v-else-if="error" :code="error.code" :message="error.message" @retry="load" />

  <Card v-else class="rounded-xl border-border/70 shadow-sm">
    <CardHeader>
      <div class="flex flex-wrap items-center gap-2">
        <CardTitle class="flex items-center gap-2 text-base font-semibold">
          <Bot class="size-4 text-primary" />
          {{ t('assistant.title') }}
        </CardTitle>
        <SysBadge v-if="config?.source === 'env'" tone="neutral">{{
          t('assistant.fromEnv')
        }}</SysBadge>
      </div>
      <CardDescription>{{ t('assistant.intro') }}</CardDescription>
    </CardHeader>

    <CardContent class="space-y-5">
      <form class="space-y-4" @submit.prevent="save">
        <div class="space-y-2">
          <Label>{{ t('assistant.provider') }}</Label>
          <Select v-model="provider">
            <SelectTrigger class="w-full sm:max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="off">{{ t('assistant.providerOff') }}</SelectItem>
              <SelectItem value="openai">{{ t('assistant.providerOpenai') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div
          v-if="provider === 'openai'"
          class="space-y-4 rounded-xl border border-border/60 bg-muted/15 p-4"
        >
          <div class="space-y-2">
            <Label for="assistant-base-url">{{ t('assistant.baseUrl') }}</Label>
            <Input
              id="assistant-base-url"
              v-model="baseUrl"
              class="font-mono text-sm"
              placeholder="https://openrouter.ai/api/v1"
            />
          </div>
          <div class="space-y-2">
            <Label for="assistant-model">{{ t('assistant.model') }}</Label>
            <Input id="assistant-model" v-model="model" required />
          </div>
          <div class="space-y-2">
            <Label for="assistant-api-key" class="flex items-center gap-1.5">
              <KeyRound class="size-3.5 text-muted-foreground" />
              {{ t('assistant.apiKey') }}
            </Label>
            <Input
              id="assistant-api-key"
              v-model="apiKey"
              type="password"
              autocomplete="off"
              :disabled="!config?.can_store_key"
              :placeholder="
                config?.has_key ? t('assistant.keyStored') : t('assistant.keyPlaceholder')
              "
            />
          </div>
          <Alert v-if="!config?.can_store_key" class="border-sys-warn/30 bg-sys-warn/5">
            <AlertDescription class="text-xs text-muted-foreground">
              {{ t('assistant.noSecretKey') }}
            </AlertDescription>
          </Alert>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <Button type="submit" size="sm" :disabled="saving">
            {{ saving ? t('assistant.saving') : t('assistant.save') }}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="gap-1.5"
            :disabled="testing || provider === 'off'"
            @click="test"
          >
            <Zap class="size-3.5" />
            {{ testing ? t('assistant.testing') : t('assistant.test') }}
          </Button>
          <Button
            v-if="config?.has_key && config.source === 'store'"
            type="button"
            variant="ghost"
            size="sm"
            :disabled="saving"
            @click="clearKey"
          >
            {{ t('assistant.clearKey') }}
          </Button>
        </div>
      </form>

      <Separator />

      <dl class="grid gap-2 text-sm sm:grid-cols-2">
        <Field :label="t('assistant.verified')">
          <span :class="config?.verified_at ? 'text-foreground' : 'text-sys-warn'">
            {{ config?.verified_at ? when(config.verified_at) : t('assistant.neverVerified') }}
          </span>
        </Field>
        <Field v-if="config?.updated_at" :label="t('assistant.updated')">
          {{ when(config.updated_at) }} · {{ config.updated_by }}
        </Field>
      </dl>

      <Alert
        v-if="probe"
        :variant="probe.ok ? 'default' : 'destructive'"
        :class="probe.ok ? 'border-border/60 bg-muted/20' : undefined"
      >
        <AlertDescription class="text-sm">
          {{
            probe.ok
              ? t('assistant.probeOk', { provider: probe.provider, reply: probe.reply })
              : t('assistant.probeFailed', { error: probe.error ?? '' })
          }}
        </AlertDescription>
      </Alert>
    </CardContent>
  </Card>
</template>
