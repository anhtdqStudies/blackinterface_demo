<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription, AlertTitle } from '@/ui/alert'
import { Button } from '@/ui/button'

defineProps<{
  code: string
  message: string
  class?: string
}>()

const emit = defineEmits<{ retry: [] }>()
const { t } = useI18n()
</script>

<template>
  <div
    :class="
      cn('flex h-full flex-col items-center justify-center gap-3 p-4 text-center', $props.class)
    "
    role="alert"
  >
    <Alert variant="destructive" class="max-w-md">
      <AlertTitle>{{ t('ui.errorTitle') }}</AlertTitle>
      <AlertDescription>{{ message }}</AlertDescription>
    </Alert>
    <p class="m-0 font-mono text-2xs text-sys-idle">{{ code }}</p>
    <Button variant="outline" size="sm" @click="emit('retry')">
      {{ t('ui.retry') }}
    </Button>
  </div>
</template>
