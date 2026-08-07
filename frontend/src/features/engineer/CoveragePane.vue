<script setup lang="ts">
/**
 * How much of the station the model covers — engineering surface.
 */
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { bayScope, opsPath } from '@/router'
import { useStructureStore } from '@/stores/structure'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import Field from '@/ui/Field.vue'
import Panel from '@/ui/Panel.vue'
import Skeleton from '@/ui/Skeleton.vue'

const { t } = useI18n()
const structure = useStructureStore()
const workspace = useWorkspaceStore()

function retry(): void {
  void structure.load()
}
</script>

<template>
  <div class="p-3">
    <Skeleton v-if="structure.loading" variant="row" :count="5" />
    <ErrorBox
      v-else-if="structure.error"
      :code="structure.error.code"
      :message="structure.error.message"
      @retry="retry"
    />
    <template v-else-if="structure.station">
      <Panel :title="t('coverage.title')">
        <Field :label="t('coverage.devices')">
          <b>{{ structure.station.coverage.devices }}</b>
        </Field>
        <Field :label="t('coverage.positionGood')">
          <b>{{ structure.station.coverage.position_good }}</b>
          / {{ structure.station.coverage.devices }}
        </Field>
        <Field :label="t('coverage.determined')">
          <b>{{ structure.station.coverage.position_determined }}</b>
          / {{ structure.station.coverage.devices }}
        </Field>
        <Field :label="t('coverage.nodes')">{{ structure.station.node_count }}</Field>
      </Panel>

      <Panel :title="t('coverage.baysAt', { level: workspace.voltageLevel ?? '' })">
        <RouterLink
          v-for="bay in structure.baysAt(workspace.voltageLevel)"
          :key="bay.id"
          class="mb-1 flex items-center justify-between gap-2 rounded-[var(--radius)] border border-line px-2 py-1 text-sm text-fg no-underline last:mb-0 hover:border-accent"
          :to="opsPath(bayScope(bay.id))"
        >
          <span>
            {{ bay.name }}
            <small class="text-dim">{{ bay.template_id ?? t('coverage.noTemplate') }}</small>
          </span>
          <span class="rounded-full border border-line px-1.5 text-2xs text-dim">
            {{ bay.bay_type }}
          </span>
        </RouterLink>
      </Panel>
    </template>
    <Empty v-else :reason="t('pane.noModel')" />
  </div>
</template>
