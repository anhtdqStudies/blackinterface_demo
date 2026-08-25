<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Quality, SwitchState } from '@/api/client'
import { cn } from '@/lib/utils'
import { Badge } from '@/ui/badge'

const props = defineProps<{ state: SwitchState; quality?: Quality; class?: string }>()

const { t } = useI18n()

const toneClass = computed(
  () =>
    ({
      CLOSED: 'border-st-closed/40 text-st-closed',
      OPEN: 'border-st-open/40 text-st-open',
      INTERMEDIATE: 'border-st-intermediate/40 text-st-intermediate',
      UNDETERMINED: 'border-st-undetermined/40 text-st-undetermined',
    })[props.state],
)
</script>

<template>
  <Badge
    variant="outline"
    :class="cn('font-mono text-2xs font-normal tabular-nums', toneClass, props.class)"
  >
    {{ t(`state.${state}`) }}
    <span v-if="quality" class="text-muted-foreground">· {{ quality }}</span>
  </Badge>
</template>
