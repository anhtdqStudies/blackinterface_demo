<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApiError, api, type AssistantConfig, type AssistantProbe } from '@/api/client'
import SysBadge from '@/ui/SysBadge.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import Field from '@/ui/Field.vue'
import Panel from '@/ui/Panel.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Button } from '@/ui/button'
import { Input } from '@/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'

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
  <div class="p-3">
    <PaneSkeleton v-if="loading" variant="row" :count="3" />
    <ErrorBox v-else-if="error" :code="error.code" :message="error.message" @retry="load" />

    <Panel v-else :title="t('assistant.title')">
      <template #title-extra>
        <SysBadge v-if="config?.source === 'env'" tone="neutral">{{
          t('assistant.fromEnv')
        }}</SysBadge>
      </template>

      <p class="mb-3 text-xs text-muted-foreground">{{ t('assistant.intro') }}</p>

      <form class="flex flex-col gap-3" @submit.prevent="save">
        <Field :label="t('assistant.provider')" :numeric="false">
          <Select v-model="provider">
            <SelectTrigger class="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="off">{{ t('assistant.providerOff') }}</SelectItem>
              <SelectItem value="openai">{{ t('assistant.providerOpenai') }}</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <template v-if="provider === 'openai'">
          <Field :label="t('assistant.baseUrl')" :numeric="false">
            <Input v-model="baseUrl" placeholder="https://openrouter.ai/api/v1" />
          </Field>
          <Field :label="t('assistant.model')" :numeric="false">
            <Input v-model="model" required />
          </Field>
          <Field :label="t('assistant.apiKey')" :numeric="false">
            <Input
              v-model="apiKey"
              type="password"
              autocomplete="off"
              :disabled="!config?.can_store_key"
              :placeholder="
                config?.has_key ? t('assistant.keyStored') : t('assistant.keyPlaceholder')
              "
            />
          </Field>
          <p v-if="!config?.can_store_key" class="m-0 text-xs text-sys-warn">
            {{ t('assistant.noSecretKey') }}
          </p>
        </template>

        <div class="flex flex-wrap items-center gap-2">
          <Button type="submit" size="sm" :disabled="saving">
            {{ saving ? t('assistant.saving') : t('assistant.save') }}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="testing || provider === 'off'"
            @click="test"
          >
            {{ testing ? t('assistant.testing') : t('assistant.test') }}
          </Button>
          <Button
            v-if="config?.has_key && config.source === 'store'"
            type="button"
            variant="outline"
            size="sm"
            :disabled="saving"
            @click="clearKey"
          >
            {{ t('assistant.clearKey') }}
          </Button>
        </div>
      </form>

      <dl class="mt-3 text-xs">
        <Field :label="t('assistant.verified')">
          <span :class="config?.verified_at ? 'text-foreground' : 'text-sys-warn'">
            {{ config?.verified_at ? when(config.verified_at) : t('assistant.neverVerified') }}
          </span>
        </Field>
        <Field v-if="config?.updated_at" :label="t('assistant.updated')">
          {{ when(config.updated_at) }} · {{ config.updated_by }}
        </Field>
      </dl>

      <p
        v-if="probe"
        class="m-0 mt-2 text-xs"
        :class="probe.ok ? 'text-foreground' : 'text-sys-down'"
      >
        {{
          probe.ok
            ? t('assistant.probeOk', { provider: probe.provider, reply: probe.reply })
            : t('assistant.probeFailed', { error: probe.error ?? '' })
        }}
      </p>
    </Panel>
  </div>
</template>
