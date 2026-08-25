<script setup lang="ts">
/**
 * Analog readings for the scope this pane follows (ADR-0012).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Gauge } from 'lucide-vue-next'
import type { Reading } from '@/api/client'
import type { PaneProps } from '@/app/layout/panes'
import { formatScope } from '@/scope'
import { useMeasurementsStore } from '@/stores/measurements'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'
import DataTable, { type DataTableColumn } from '@/ui/DataTable.vue'
import Empty from '@/ui/Empty.vue'
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
  <div class="w-full space-y-4">
    <div class="rounded-lg border border-border/60 bg-muted/20 px-4 py-2.5">
      <p class="flex items-center gap-2 text-sm text-muted-foreground">
        <Gauge class="size-4 shrink-0 text-primary" />
        {{ t('measurement.scopeLine', { scope: scopeKey }) }}
      </p>
    </div>

    <PaneSkeleton v-if="!measurements.loaded" variant="row" :count="5" />

    <Card v-else-if="readings.length" class="border-border/60 py-0 shadow-none">
      <CardHeader class="border-b border-border/60 px-4 py-3">
        <CardTitle class="text-sm font-medium">{{ t('measurement.title') }}</CardTitle>
      </CardHeader>
      <CardContent class="px-0 pb-0">
        <p v-if="fromParentScope" class="px-4 pb-2 text-xs text-muted-foreground">
          {{ t('measurement.fromScope', { scope: readingScopeKey }) }}
        </p>
        <DataTable :columns="columns" :rows="readings" :row-key="(row) => row.id" framed>
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

        <p class="border-t border-border/60 px-4 py-3 text-xs text-muted-foreground">
          {{ t('measurement.deadbandNote') }}
          <template v-if="measurements.deadbandOverride !== null">
            {{ t('measurement.deadbandOverride', { pct: measurements.deadbandOverride }) }}
          </template>
        </p>
      </CardContent>
    </Card>

    <Empty v-else :reason="t('pane.noMeasurements')" />
  </div>
</template>
