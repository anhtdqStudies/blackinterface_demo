<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProjectsStore } from '@/stores/projects'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import Field from '@/ui/Field.vue'
import Panel from '@/ui/Panel.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Card, CardContent } from '@/ui/card'
import { Input } from '@/ui/input'

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
    <PaneSkeleton
      v-if="store.loading && store.projects.length === 0"
      variant="row"
      :count="3"
    />

    <Panel v-else :title="t('pane.connections')">
      <p class="mb-3 text-xs text-muted-foreground">{{ t('projects.newIntro') }}</p>

      <form class="mb-3 flex flex-wrap items-end gap-3" @submit.prevent="create">
        <Field :label="t('projects.name')">
          <Input
            v-model="name"
            class="min-w-[200px]"
            :placeholder="t('projects.namePlaceholder')"
            required
          />
        </Field>
        <Field :label="t('projects.address')">
          <Input
            v-model="url"
            class="min-w-[260px] font-mono"
            placeholder="opc.tcp://host:48050"
            required
          />
        </Field>
        <Button type="submit" size="sm" :disabled="store.busyId !== null">
          {{ store.busyId === -1 ? t('projects.connecting') : t('projects.connect') }}
        </Button>
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
        · <span class="text-muted-foreground">{{ t('projects.retryHint') }}</span>
      </p>

      <Empty v-if="store.projects.length === 0" :reason="t('projects.none')" />

      <ul v-else class="flex flex-col gap-2">
        <li v-for="p in store.projects" :key="p.id">
          <Card :class="p.active ? 'border-primary' : ''">
            <CardContent
              class="grid grid-cols-[1.2fr_1fr_auto] items-center gap-3 px-3 py-2 text-sm"
            >
              <div>
                <b>{{ p.name }}</b>
                <Badge v-if="p.active" class="ml-2">{{ t('projects.active') }}</Badge>
                <br />
                <code class="text-2xs text-muted-foreground">{{ p.opcua_url }}</code>
              </div>
              <div class="text-2xs text-muted-foreground">
                <template v-if="p.has_snapshot">
                  {{ p.model_name || '?' }} · ModelVersion {{ p.model_version ?? '?' }}
                  <br />
                  {{ t('projects.snapshot', { when: short(p.snapshot_saved_at) }) }}
                </template>
                <template v-else>{{ t('projects.noSnapshot') }}</template>
              </div>
              <div class="flex gap-1">
                <Button
                  variant="outline"
                  size="xs"
                  :disabled="store.busyId !== null || !p.has_snapshot"
                  @click="store.open(p.id)"
                >
                  {{ store.busyId === p.id ? t('projects.opening') : t('projects.open') }}
                </Button>
                <Button
                  variant="outline"
                  size="xs"
                  :disabled="store.busyId !== null"
                  @click="store.refresh(p.id)"
                >
                  {{ t('projects.refresh') }}
                </Button>
                <Button
                  variant="outline"
                  size="xs"
                  :disabled="store.busyId !== null"
                  @click="remove(p.id, p.name)"
                >
                  {{ t('projects.remove') }}
                </Button>
              </div>
            </CardContent>
          </Card>
        </li>
      </ul>
    </Panel>
  </div>
</template>
