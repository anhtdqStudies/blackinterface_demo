<script setup lang="ts" generic="T extends Record<string, unknown>">
import { computed, ref } from 'vue'
import { cn } from '@/lib/utils'

/**
 * A scrollable table with optional client-side sorting.
 *
 * Cell content is always a slot — this component owns layout and sort chrome
 * only, not domain columns.
 */
export type DataTableColumn<T> = {
  id: string
  label: string
  sortable?: boolean
  align?: 'left' | 'right'
  sortValue?: (row: T) => string | number | null
}

const props = defineProps<{
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string
  class?: string
}>()

const sortColumnId = ref<string | null>(null)
const sortDirection = ref<'asc' | 'desc'>('asc')

const sortedRows = computed(() => {
  if (!sortColumnId.value) return props.rows
  const column = props.columns.find((entry) => entry.id === sortColumnId.value)
  if (!column?.sortValue) return props.rows

  const direction = sortDirection.value === 'asc' ? 1 : -1
  return [...props.rows].sort((left, right) => {
    const a = column.sortValue!(left)
    const b = column.sortValue!(right)
    if (a == null && b == null) return 0
    if (a == null) return 1
    if (b == null) return -1
    if (typeof a === 'number' && typeof b === 'number') return (a - b) * direction
    return String(a).localeCompare(String(b), undefined, { numeric: true }) * direction
  })
})

function toggleSort(columnId: string): void {
  const column = props.columns.find((entry) => entry.id === columnId)
  if (!column?.sortable) return
  if (sortColumnId.value === columnId) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortColumnId.value = columnId
  sortDirection.value = 'asc'
}

function sortLabel(columnId: string): string {
  if (sortColumnId.value !== columnId) return '↕'
  return sortDirection.value === 'asc' ? '↑' : '↓'
}
</script>

<template>
  <div :class="cn('overflow-x-auto', props.class)">
    <table class="w-full min-w-full text-sm">
      <thead>
        <tr class="border-b border-line text-xs tracking-[0.06em] text-dim uppercase">
          <th
            v-for="column in columns"
            :key="column.id"
            :class="cn('py-1 pr-2 font-semibold', column.align === 'right' && 'text-right')"
            :aria-sort="
              sortColumnId === column.id
                ? sortDirection === 'asc'
                  ? 'ascending'
                  : 'descending'
                : undefined
            "
          >
            <button
              v-if="column.sortable"
              type="button"
              class="inline-flex items-center gap-1 border-0 bg-transparent p-0 text-inherit"
              @click="toggleSort(column.id)"
            >
              {{ column.label }}
              <span class="text-2xs text-sys-idle" aria-hidden="true">{{
                sortLabel(column.id)
              }}</span>
            </button>
            <span v-else>{{ column.label }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in sortedRows"
          :key="rowKey(row)"
          class="align-baseline border-b border-line/40 last:border-0"
        >
          <td
            v-for="column in columns"
            :key="column.id"
            :class="cn('py-[3px] pr-2', column.align === 'right' && 'text-right')"
          >
            <slot :name="`cell-${column.id}`" :row="row" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
