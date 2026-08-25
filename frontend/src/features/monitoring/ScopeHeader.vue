<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronLeft } from 'lucide-vue-next'
import { formatScope, parentScope, type ScopeRef } from '@/scope'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'

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

const scopeKindLabel = computed(() => {
  const kind = props.scope.kind
  if (kind === 'station') return t('inspector.wholeStation')
  return kind
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
  <div class="shrink-0 border-b border-border px-4 py-2.5">
    <Button
      v-if="canGoUp"
      variant="ghost"
      size="xs"
      class="-ml-2 mb-1 h-auto gap-1 px-2 py-1 text-muted-foreground hover:text-foreground"
      @click="workspace.up()"
    >
      <ChevronLeft class="size-3.5" />
      {{ backLabel }}
    </Button>

    <div class="flex flex-wrap items-center gap-2">
      <h2 class="m-0 text-lg font-semibold leading-tight tracking-tight text-foreground">
        {{ primary }}
      </h2>
      <Badge variant="outline" class="font-mono text-2xs font-normal capitalize">
        {{ scopeKindLabel }}
      </Badge>
    </div>

    <p v-if="secondary" class="m-0 mt-1 text-sm text-muted-foreground">{{ secondary }}</p>
  </div>
</template>
