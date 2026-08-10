<script setup lang="ts">
import { cn } from '@/lib/utils'
import { Card, CardHeader, CardTitle } from '@/ui/card'

defineProps<{ title?: string; class?: string }>()
</script>

<template>
  <section :class="cn('mb-3', $props.class)">
    <Card v-if="title" class="gap-2 border-0 bg-transparent py-0 shadow-none">
      <CardHeader class="px-0 py-0">
        <CardTitle class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          {{ title }}
          <slot name="title-extra" />
        </CardTitle>
      </CardHeader>
    </Card>
    <slot />
  </section>
</template>
