<script setup lang="ts" generic="T extends Record<string, unknown>">
import { computed, ref } from 'vue'
import { cn } from '@/lib/utils'
import { Button } from '@/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/ui/table'

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
  defaultSortColumn?: string
  defaultSortDirection?: 'asc' | 'desc'
  /** When true, wraps the table in a bordered card shell. */
  framed?: boolean
}>()

const sortColumnId = ref<string | null>(props.defaultSortColumn ?? null)
const sortDirection = ref<'asc' | 'desc'>(props.defaultSortDirection ?? 'asc')

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
  <div
    :class="
      cn(
        'overflow-x-auto',
        framed && 'overflow-hidden rounded-xl border border-border/70 bg-card shadow-sm',
        props.class,
      )
    "
  >
    <Table class="text-sm">
      <TableHeader
        :class="framed ? 'sticky top-0 z-10 bg-muted/40 backdrop-blur-sm' : undefined"
      >
        <TableRow class="border-border/60 hover:bg-transparent">
          <TableHead
            v-for="column in columns"
            :key="column.id"
            :class="
              cn(
                'h-10 text-xs font-medium tracking-wide text-muted-foreground uppercase',
                column.align === 'right' && 'text-right',
              )
            "
            :aria-sort="
              sortColumnId === column.id
                ? sortDirection === 'asc'
                  ? 'ascending'
                  : 'descending'
                : undefined
            "
          >
            <Button
              v-if="column.sortable"
              variant="ghost"
              size="xs"
              class="h-auto gap-1 px-0 font-medium text-inherit uppercase hover:bg-transparent hover:text-foreground"
              @click="toggleSort(column.id)"
            >
              {{ column.label }}
              <span class="text-2xs text-muted-foreground" aria-hidden="true">{{
                sortLabel(column.id)
              }}</span>
            </Button>
            <span v-else>{{ column.label }}</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow
          v-for="(row, index) in sortedRows"
          :key="rowKey(row)"
          :class="cn(index % 2 === 1 && framed && 'bg-muted/15')"
        >
          <TableCell
            v-for="column in columns"
            :key="column.id"
            :class="cn('py-2.5', column.align === 'right' && 'text-right')"
          >
            <slot :name="`cell-${column.id}`" :row="row" />
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
