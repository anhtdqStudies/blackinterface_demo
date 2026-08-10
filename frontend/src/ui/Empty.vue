<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Alert, AlertDescription } from '@/ui/alert'

defineProps<{
  reason: string
  action?: { label: string; to: string }
}>()
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-2 p-4 text-center">
    <Alert class="max-w-md border-dashed bg-transparent">
      <AlertDescription class="text-sm text-muted-foreground">{{ reason }}</AlertDescription>
    </Alert>
    <RouterLink v-if="action" :to="action.to" class="text-sm text-primary">{{
      action.label
    }}</RouterLink>
  </div>
</template>
