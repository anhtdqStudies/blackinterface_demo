<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Link2, Plus, Trash2 } from 'lucide-vue-next'
import { useProjectsStore } from '@/stores/projects'
import Empty from '@/ui/Empty.vue'
import ErrorBox from '@/ui/ErrorBox.vue'
import PaneSkeleton from '@/ui/PaneSkeleton.vue'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/ui/card'
import { Input } from '@/ui/input'
import { Label } from '@/ui/label'

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
  <PaneSkeleton v-if="store.loading && store.projects.length === 0" variant="row" :count="3" />

  <Card v-else class="rounded-xl border-border/70 shadow-sm">
    <CardHeader>
      <CardTitle class="flex items-center gap-2 text-base font-semibold">
        <Link2 class="size-4 text-primary" />
        {{ t('pane.connections') }}
      </CardTitle>
      <CardDescription>{{ t('projects.newIntro') }}</CardDescription>
    </CardHeader>

    <CardContent class="space-y-4">
      <form
        class="grid gap-4 rounded-xl border border-border/60 bg-muted/20 p-4 sm:grid-cols-2"
        @submit.prevent="create"
      >
        <div class="space-y-2 sm:col-span-2 sm:max-w-xs">
          <Label for="project-name">{{ t('projects.name') }}</Label>
          <Input
            id="project-name"
            v-model="name"
            :placeholder="t('projects.namePlaceholder')"
            required
          />
        </div>
        <div class="space-y-2 sm:col-span-2">
          <Label for="project-url">{{ t('projects.address') }}</Label>
          <Input
            id="project-url"
            v-model="url"
            class="font-mono text-sm"
            placeholder="opc.tcp://host:48050"
            required
          />
        </div>
        <div class="sm:col-span-2">
          <Button type="submit" size="sm" class="gap-1.5" :disabled="store.busyId !== null">
            <Plus class="size-3.5" />
            {{ store.busyId === -1 ? t('projects.connecting') : t('projects.connect') }}
          </Button>
        </div>
      </form>

      <ErrorBox
        v-if="store.error"
        :code="store.error.code"
        :message="store.error.message"
        @retry="store.fetchList()"
      />
      <p
        v-else-if="store.lastLoadError"
        class="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
      >
        {{ t('projects.sourceUnreadable') }}
        <code class="mt-1 block font-mono text-2xs opacity-90">{{ store.lastLoadError }}</code>
        <span class="mt-1 block text-muted-foreground">{{ t('projects.retryHint') }}</span>
      </p>

      <Empty v-if="store.projects.length === 0" :reason="t('projects.none')" />

      <ul v-else class="flex flex-col gap-3">
        <li v-for="p in store.projects" :key="p.id">
          <Card
            class="overflow-hidden transition-colors"
            :class="p.active ? 'border-primary/50 bg-primary/5' : 'border-border/60'"
          >
            <CardContent class="space-y-3 p-4">
              <div class="flex flex-wrap items-start gap-2">
                <div class="min-w-0 flex-1">
                  <p class="font-medium text-foreground">{{ p.name }}</p>
                  <code class="mt-0.5 block truncate font-mono text-2xs text-muted-foreground">
                    {{ p.opcua_url }}
                  </code>
                </div>
                <Badge v-if="p.active" variant="secondary" class="bg-primary/15 text-primary">
                  {{ t('projects.active') }}
                </Badge>
              </div>

              <p class="text-xs leading-relaxed text-muted-foreground">
                <template v-if="p.has_snapshot">
                  {{ p.model_name || '?' }} · ModelVersion {{ p.model_version ?? '?' }}
                  <br />
                  {{ t('projects.snapshot', { when: short(p.snapshot_saved_at) }) }}
                </template>
                <template v-else>{{ t('projects.noSnapshot') }}</template>
              </p>

              <div class="flex flex-wrap gap-2">
                <Button
                  variant="default"
                  size="sm"
                  :disabled="store.busyId !== null || !p.has_snapshot"
                  @click="store.open(p.id)"
                >
                  {{ store.busyId === p.id ? t('projects.opening') : t('projects.open') }}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="store.busyId !== null"
                  @click="store.refresh(p.id)"
                >
                  {{ t('projects.refresh') }}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="text-muted-foreground hover:text-destructive"
                  :disabled="store.busyId !== null"
                  @click="remove(p.id, p.name)"
                >
                  <Trash2 class="size-3.5" />
                  {{ t('projects.remove') }}
                </Button>
              </div>
            </CardContent>
          </Card>
        </li>
      </ul>
    </CardContent>
  </Card>
</template>
