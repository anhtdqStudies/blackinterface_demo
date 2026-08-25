<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUp } from 'lucide-vue-next'
import { STATION, scopesEqual } from '@/scope'
import { useWorkspaceStore } from '@/stores/workspace'
import { Badge } from '@/ui/badge'
import { Button } from '@/ui/button'
import { Textarea } from '@/ui/textarea'

const props = defineProps<{ busy: boolean; scope: string }>()
const emit = defineEmits<{ ask: [question: string] }>()

const { t } = useI18n()
const workspace = useWorkspaceStore()
const draft = ref('')

const canScopeUp = computed(() => !scopesEqual(workspace.scope, STATION))
const canSend = computed(() => Boolean(draft.value.trim()) && !props.busy)

function submit(): void {
  const question = draft.value.trim()
  if (!question || props.busy) return
  draft.value = ''
  emit('ask', question)
}

function onScopeChipClick(): void {
  if (canScopeUp.value) workspace.up()
}
</script>

<template>
  <form class="shrink-0 px-4 pb-4 pt-2" @submit.prevent="submit">
    <div
      class="mx-auto flex max-w-3xl flex-col gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm transition-shadow focus-within:border-primary/40 focus-within:shadow-md focus-within:ring-2 focus-within:ring-ring/30"
    >
      <Textarea
        v-model="draft"
        rows="2"
        :placeholder="t('chat.placeholder')"
        :disabled="busy"
        class="min-h-[3.25rem] resize-none border-0 bg-transparent px-3 py-2 text-sm shadow-none focus-visible:ring-0"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="flex items-center gap-2 px-1 pb-1">
        <Badge
          variant="secondary"
          class="max-w-[min(100%,14rem)] cursor-default truncate font-mono text-2xs font-normal"
          :title="t('scope.chipHint', { scope })"
          :class="{ 'cursor-pointer hover:bg-secondary/80': canScopeUp }"
          @click="onScopeChipClick"
        >
          {{ t('scope.chip', { scope }) }}
        </Badge>
        <Button
          type="submit"
          size="icon-sm"
          class="ml-auto rounded-full"
          :disabled="!canSend"
          :title="busy ? t('chat.sending') : t('chat.send')"
          :aria-label="busy ? t('chat.sending') : t('chat.send')"
        >
          <ArrowUp />
        </Button>
      </div>
    </div>
  </form>
</template>
