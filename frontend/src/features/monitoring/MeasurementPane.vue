<script setup lang="ts">
/**
 * Analog readings for the scope this pane follows (ADR-0012).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Reading } from '@/api/client'
import type { PaneProps } from '@/app/layout/panes'
import { formatScope } from '@/scope'
import { useMeasurementsStore } from '@/stores/measurements'
import DataTable, { type DataTableColumn } from '@/ui/DataTable.vue'
import Empty from '@/ui/Empty.vue'
import Panel from '@/ui/Panel.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import ValueCell from '@/ui/ValueCell.vue'

const props = defineProps<PaneProps>()

const { t } = useI18n()
const measurements = useMeasurementsStore()

const scopeKey = computed(() => formatScope(props.scope))
const readingScopeKey = computed(() => measurements.resolveScope(props.scope))
const readings = computed(() => measurements.forPane(props.scope))
const fromParentScope = computed(() => readingScopeKey.value !== scopeKey.value)

const columns = computed<DataTableColumn<Reading>[]>(() => [
  {
    id: 'quantity',
    label: t('measurement.columnQuantity'),
    sortable: true,
    sortValue: (row) => t(`quantity.${row.quantity}`),
  },
  {
    id: 'value',
    label: t('measurement.columnValue'),
    align: 'right',
    sortable: true,
    sortValue: (row) => (row.quality === 'GOOD' && row.value != null ? row.value : null),
  },
])
</script>

<template>
  <div class="p-3">
    <PaneSkeleton v-if="!measurements.loaded" variant="row" :count="5" />
    <Panel v-else-if="readings.length" :title="t('measurement.title')">
      <p v-if="fromParentScope" class="mb-2 text-xs text-dim">
        {{ t('measurement.fromScope', { scope: readingScopeKey }) }}
      </p>
      <DataTable :columns="columns" :rows="readings" :row-key="(row) => row.id">
        <template #cell-quantity="{ row }">
          {{ t(`quantity.${row.quantity}`) }}
        </template>
        <template #cell-value="{ row }">
          <ValueCell
            :value="row.value ?? null"
            :quality="row.quality"
            :unit="row.unit"
            :quantity="row.quantity"
            :source-point="row.measurand"
          />
        </template>
      </DataTable>

      <p class="mt-2 text-xs text-dim">
        {{ t('measurement.deadbandNote') }}
        <template v-if="measurements.deadbandOverride !== null">
          {{ t('measurement.deadbandOverride', { pct: measurements.deadbandOverride }) }}
        </template>
      </p>
    </Panel>
    <Empty v-else :reason="t('pane.noMeasurements')" />
  </div>
</template>
