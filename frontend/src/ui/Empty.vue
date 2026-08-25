<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Inbox } from 'lucide-vue-next'
import { Alert, AlertDescription } from '@/ui/alert'

defineProps<{
  reason: string
  action?: { label: string; to: string }
}>()
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
    <span
      class="flex size-12 items-center justify-center rounded-full border border-dashed border-border bg-muted/30 text-muted-foreground"
    >
      <Inbox class="size-5" />
    </span>
    <Alert class="max-w-sm border-0 bg-transparent shadow-none">
      <AlertDescription class="text-sm leading-relaxed text-muted-foreground">
        {{ reason }}
      </AlertDescription>
    </Alert>
    <RouterLink
      v-if="action"
      :to="action.to"
      class="text-sm font-medium text-primary hover:underline"
    >
      {{ action.label }}
    </RouterLink>
  </div>
</template>
