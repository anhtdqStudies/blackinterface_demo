<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatScope, parentScope, type ScopeRef } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<{ scope: ScopeRef }>()

const { t } = useI18n()
const structure = useStructureStore()
const workspace = useWorkspaceStore()

const parent = computed(() => parentScope(props.scope))
const canGoUp = computed(() => parent.value !== null)

const backLabel = computed(() => {
  const p = parent.value
  if (!p) return ''
  if (p.kind === 'bay') return t('inspector.backToBay', { bay: p.id })
  return t('inspector.backToStation')
})

const primary = computed(() => {
  const s = props.scope
  if (s.kind === 'station') {
    return structure.station?.name ?? t('inspector.wholeStation')
  }
  if (s.kind === 'bay') {
    const bay = structure.bay(s.id)
    return bay?.name ? `${s.id} · ${bay.name}` : s.id
  }
  if (s.kind === 'device') {
    return s.id.split('.').pop() ?? s.id
  }
  return formatScope(s)
})

const secondary = computed(() => {
  const s = props.scope
  if (s.kind === 'station') {
    const st = structure.station
    if (!st) return null
    return t('inspector.stationMeta', {
      bays: st.bay_count,
      devices: st.device_count,
    })
  }
  if (s.kind === 'bay') {
    const bay = structure.bay(s.id)
    return bay ? `${bay.bay_type}${bay.template_id ? ` · ${bay.template_id}` : ''}` : null
  }
  if (s.kind === 'device') {
    const bayId = s.id.split('.')[0] ?? ''
    const bay = structure.bay(bayId)
    return bay ? `${bayId} · ${bay.name}` : bayId
  }
  return formatScope(s)
})
</script>

<template>
  <div class="shrink-0 bg-muted/40 px-3 py-2">
    <button
      v-if="canGoUp"
      type="button"
      class="mb-1 block border-0 bg-transparent p-0 text-2xs text-primary hover:underline"
      @click="workspace.up()"
    >
      {{ backLabel }}
    </button>
    <h2 class="m-0 text-base font-semibold leading-tight text-foreground">{{ primary }}</h2>
    <p v-if="secondary" class="m-0 mt-0.5 text-2xs text-muted-foreground">{{ secondary }}</p>
  </div>
</template>
