<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { cn } from '@/lib/utils'
import { formatMeasuredValue, isValueReadable, unitToShow } from '@/ui/valueCell'

/**
 * One number, optionally with a verified unit, gated by quality (I2, Q7).
 *
 * The only place in the frontend allowed to decide whether a unit prints.
 * Callers pass raw backend fields; this component refuses to overstate.
 */
const props = defineProps<{
  value: number | null
  quality: string
  unit?: string
  /** Affects decimal places — `power_factor` keeps three digits. */
  quantity?: string
  /** Point id for the "from {point}" tooltip when the unit is verified. */
  sourcePoint?: string
  /** Tooltip override. When omitted, a safe default is derived. */
  hint?: string
  class?: string
}>()

const { t, locale } = useI18n()

const readable = computed(() => isValueReadable(props.quality, props.value))

const shownUnit = computed(() => unitToShow(props.unit))

const display = computed(() => {
  if (!readable.value || props.value === null) return t('common.dash')
  return formatMeasuredValue(props.value, props.quantity, locale.value)
})

const title = computed(() => {
  if (props.hint) return props.hint
  if (!readable.value) return t('measurement.unreadable', { quality: props.quality })
  if (shownUnit.value && props.sourcePoint)
    return t('measurement.from', { point: props.sourcePoint })
  if (readable.value) return t('measurement.unitUnverified')
  return ''
})
</script>

<template>
  <span :class="cn('inline-block', $props.class)" :title="title">
    <span :class="readable ? 'text-fg' : 'text-sys-idle'">{{ display }}</span>
    <span v-if="readable && shownUnit" class="ml-1 text-xs text-dim">{{ shownUnit }}</span>
  </span>
</template>
