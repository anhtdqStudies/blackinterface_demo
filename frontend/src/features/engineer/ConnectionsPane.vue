<script setup lang="ts">
/**
 * Named DataServer connections — engineer surface (screens.md §3.4).
 *
 * Same behaviour as the old ProjectsView, but embedded in `#/eng` instead of
 * owning a whole route.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProjectsStore } from '@/stores/projects'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import Field from '@/ui/Field.vue'
import Panel from '@/ui/Panel.vue'
import Skeleton from '@/ui/Skeleton.vue'

const store = useProjectsStore()
const { t, locale } = useI18n()

const name = ref('')
const url = ref('opc.tcp://127.0.0.1:48050')

onMounted(() => store.fetchList())

async function create(): Promise<void> {
  if (await store.create(name.value, url.value)) name.value = ''
}

function remove(id: number, projectName: string): void {
  if (window.confirm(t('projects.confirmRemove', { name: projectName }))) {
    void store.remove(id)
  }
}

function short(iso: string | null | undefined): string {
  if (!iso) return t('common.dash')
  const date = new Date(iso)
  return isNaN(date.getTime()) ? iso : date.toLocaleString(locale.value)
}
</script>

<template>
  <div class="p-3">
    <Skeleton v-if="store.loading && store.projects.length === 0" variant="row" :count="3" />

    <Panel v-else :title="t('pane.connections')">
      <p class="mb-3 text-xs text-dim">{{ t('projects.newIntro') }}</p>

      <form class="mb-3 flex flex-wrap items-end gap-3" @submit.prevent="create">
        <Field :label="t('projects.name')">
          <input
            v-model="name"
            class="min-w-[200px] rounded-[var(--radius)] border border-line bg-panel-2 px-2 py-1 text-sm"
            :placeholder="t('projects.namePlaceholder')"
            required
          />
        </Field>
        <Field :label="t('projects.address')">
          <input
            v-model="url"
            class="min-w-[260px] rounded-[var(--radius)] border border-line bg-panel-2 px-2 py-1 font-mono text-sm"
            placeholder="opc.tcp://host:48050"
            required
          />
        </Field>
        <button type="submit" class="on text-xs" :disabled="store.busyId !== null">
          {{ store.busyId === -1 ? t('projects.connecting') : t('projects.connect') }}
        </button>
      </form>

      <ErrorBox
        v-if="store.error"
        :code="store.error.code"
        :message="store.error.message"
        @retry="store.fetchList()"
      />
      <p v-else-if="store.lastLoadError" class="mb-3 text-xs text-st-closed">
        {{ t('projects.sourceUnreadable') }}
        <code>{{ store.lastLoadError }}</code>
        · <span class="text-dim">{{ t('projects.retryHint') }}</span>
      </p>

      <Empty v-if="store.projects.length === 0" :reason="t('projects.none')" />

      <ul v-else class="flex flex-col gap-2">
        <li
          v-for="p in store.projects"
          :key="p.id"
          class="grid grid-cols-[1.2fr_1fr_auto] items-center gap-3 rounded-[var(--radius)] border border-line bg-panel-2 px-3 py-2 text-sm"
          :class="{ 'border-accent': p.active }"
        >
          <div>
            <b>{{ p.name }}</b>
            <span
              v-if="p.active"
              class="ml-2 rounded-full bg-accent px-2 py-px text-2xs font-bold text-[#08111f]"
            >
              {{ t('projects.active') }}
            </span>
            <br />
            <code class="text-2xs text-dim">{{ p.opcua_url }}</code>
          </div>
          <div class="text-2xs text-dim">
            <template v-if="p.has_snapshot">
              {{ p.model_name || '?' }} · ModelVersion {{ p.model_version ?? '?' }}
              <br />
              {{ t('projects.snapshot', { when: short(p.snapshot_saved_at) }) }}
            </template>
            <template v-else>{{ t('projects.noSnapshot') }}</template>
          </div>
          <div class="flex gap-1">
            <button
              class="text-xs"
              :disabled="store.busyId !== null || !p.has_snapshot"
              @click="store.open(p.id)"
            >
              {{ store.busyId === p.id ? t('projects.opening') : t('projects.open') }}
            </button>
            <button
              class="text-xs"
              :disabled="store.busyId !== null"
              @click="store.refresh(p.id)"
            >
              {{ t('projects.refresh') }}
            </button>
            <button
              class="text-xs"
              :disabled="store.busyId !== null"
              @click="remove(p.id, p.name)"
            >
              {{ t('projects.remove') }}
            </button>
          </div>
        </li>
      </ul>
    </Panel>
  </div>
</template>
