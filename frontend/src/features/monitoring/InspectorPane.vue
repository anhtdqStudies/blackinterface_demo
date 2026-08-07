<script setup lang="ts">
/**
 * Scope inspector — resizable sections, each with its own scroll (screens.md §3.1).
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'reka-ui'
import AnomaliesPane from '@/features/monitoring/AnomaliesPane.vue'
import EnergizationPane from '@/features/monitoring/EnergizationPane.vue'
import EvidencePane from '@/features/monitoring/EvidencePane.vue'
import InspectorSection from '@/features/monitoring/InspectorSection.vue'
import MeasurementPane from '@/features/monitoring/MeasurementPane.vue'
import ScopeHeader from '@/features/monitoring/ScopeHeader.vue'
import StatePane from '@/features/monitoring/StatePane.vue'
import type { PaneProps } from '@/app/layout/panes'
import { STATION, scopesEqual } from '@/scope'
import { useMeasurementsStore } from '@/stores/measurements'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const structure = useStructureStore()
const workspace = useWorkspaceStore()
const measurements = useMeasurementsStore()

type SectionId = 'state' | 'measurements' | 'energization' | 'anomalies' | 'evidence'

type OpenMap = Record<SectionId, boolean>

interface PanelHandle {
  collapse: () => void
  expand: () => void
}

/** Collapsed panel height — header only (% of inspector column). */
const COLLAPSED = 9

const SECTIONS: ReadonlyArray<{ id: SectionId; defaultSize: number }> = [
  { id: 'state', defaultSize: 24 },
  { id: 'measurements', defaultSize: 24 },
  { id: 'energization', defaultSize: 20 },
  { id: 'anomalies', defaultSize: 16 },
  { id: 'evidence', defaultSize: 16 },
]

function panelId(id: SectionId): string {
  return `inspector-${id}`
}

function openStorageKey(): string {
  return `bi.inspector.open.${workspace.preset}`
}

function loadOpen(): OpenMap {
  try {
    const raw = localStorage.getItem(openStorageKey())
    if (raw) return { ...defaultOpen(), ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return defaultOpen()
}

function defaultOpen(): OpenMap {
  const hasAnomaly = structure.issues.some((i) => i.group === 'C')
  const scoped = !scopesEqual(props.scope, STATION)
  return {
    state: scoped,
    measurements: scoped && measurements.hasForPane(props.scope),
    energization: scoped,
    anomalies: hasAnomaly,
    evidence: false,
  }
}

const open = ref<OpenMap>(loadOpen())
const panelRefs = ref<Partial<Record<SectionId, PanelHandle>>>({})

const saveId = computed(() => `bi.inspector.sections.${workspace.preset}`)

watch(
  () => workspace.preset,
  async () => {
    open.value = loadOpen()
    await applyOpenState()
  },
)

watch(open, (next) => localStorage.setItem(openStorageKey(), JSON.stringify(next)), {
  deep: true,
})

const anomalyCount = computed(() => structure.issues.filter((i) => i.group === 'C').length)

function setPanelRef(id: SectionId, el: unknown): void {
  if (el && typeof el === 'object' && 'collapse' in el && 'expand' in el) {
    panelRefs.value[id] = el as PanelHandle
  }
}

function onCollapse(id: SectionId): void {
  open.value[id] = false
}

function onExpand(id: SectionId): void {
  open.value[id] = true
}

function toggleSection(id: SectionId): void {
  const panel = panelRefs.value[id]
  if (!panel) return
  if (open.value[id]) panel.collapse()
  else panel.expand()
}

async function applyOpenState(): Promise<void> {
  await nextTick()
  for (const sec of SECTIONS) {
    const panel = panelRefs.value[sec.id]
    if (!panel) continue
    if (open.value[sec.id]) panel.expand()
    else panel.collapse()
  }
}

onMounted(() => {
  void applyOpenState()
})

function titleFor(id: SectionId): string {
  const keys: Record<SectionId, string> = {
    state: 'pane.state',
    measurements: 'pane.measurements',
    energization: 'pane.energization',
    anomalies: 'pane.anomalies',
    evidence: 'pane.evidence',
  }
  return t(keys[id])
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col bg-panel">
    <ScopeHeader :scope="scope" />

    <SplitterGroup direction="vertical" :auto-save-id="saveId" class="min-h-0 flex-1 py-1">
      <template v-for="(sec, index) in SECTIONS" :key="sec.id">
        <SplitterResizeHandle
          v-if="index > 0"
          class="inspector-resize mx-2 flex h-2 shrink-0 cursor-row-resize items-center justify-center"
        >
          <span class="h-0.5 w-10 rounded-full bg-line" aria-hidden="true" />
        </SplitterResizeHandle>

        <SplitterPanel
          :id="panelId(sec.id)"
          :ref="(el) => setPanelRef(sec.id, el)"
          collapsible
          :collapsed-size="COLLAPSED"
          :min-size="COLLAPSED"
          :default-size="sec.defaultSize"
          class="min-h-0"
          @collapse="onCollapse(sec.id)"
          @expand="onExpand(sec.id)"
        >
          <InspectorSection
            v-model:open="open[sec.id]"
            :title="titleFor(sec.id)"
            :badge="sec.id === 'anomalies' ? anomalyCount : undefined"
            badge-tone="down"
            @toggle="toggleSection(sec.id)"
          >
            <StatePane v-if="sec.id === 'state'" :pane="pane" :scope="scope" />
            <MeasurementPane
              v-else-if="sec.id === 'measurements'"
              :pane="pane"
              :scope="scope"
            />
            <EnergizationPane
              v-else-if="sec.id === 'energization'"
              :pane="pane"
              :scope="scope"
            />
            <AnomaliesPane v-else-if="sec.id === 'anomalies'" :pane="pane" :scope="scope" />
            <EvidencePane v-else-if="sec.id === 'evidence'" :pane="pane" :scope="scope" />
          </InspectorSection>
        </SplitterPanel>
      </template>
    </SplitterGroup>
  </div>
</template>

<style scoped>
.inspector-resize:hover span,
.inspector-resize[data-state='drag'] span {
  background: var(--color-accent);
}
</style>
