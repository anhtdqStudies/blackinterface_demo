<script setup lang="ts">
/**
 * What the inspector column is describing — human title, not the raw scope ref.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { STATION, formatScope, type ScopeRef } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<{ scope: ScopeRef }>()

const { t } = useI18n()
const structure = useStructureStore()
const workspace = useWorkspaceStore()

const canGoUp = computed(() => props.scope.kind !== 'station')

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
  <div class="shrink-0 border-b border-line bg-panel-2 px-3 py-2">
    <button
      v-if="canGoUp"
      type="button"
      class="mb-1 block border-0 bg-transparent p-0 text-2xs text-accent hover:underline"
      @click="workspace.go(STATION)"
    >
      {{ t('inspector.backToStation') }}
    </button>
    <h2 class="m-0 text-base font-semibold leading-tight text-fg">{{ primary }}</h2>
    <p v-if="secondary" class="m-0 mt-0.5 text-2xs text-dim">{{ secondary }}</p>
  </div>
</template>
