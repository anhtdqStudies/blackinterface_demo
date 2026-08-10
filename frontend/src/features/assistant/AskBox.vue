<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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
  <form
    class="flex shrink-0 flex-col gap-2 border-t border-border p-3"
    @submit.prevent="submit"
  >
    <Textarea
      v-model="draft"
      rows="2"
      :placeholder="t('chat.placeholder')"
      :disabled="busy"
      class="min-h-0 resize-none text-sm"
      @keydown.enter.exact.prevent="submit"
    />
    <div class="flex items-center gap-2">
      <Badge
        variant="secondary"
        class="max-w-[min(100%,14rem)] cursor-default truncate font-mono text-2xs font-normal"
        :title="t('scope.chipHint', { scope })"
        :class="{ 'cursor-pointer hover:bg-secondary/80': canScopeUp }"
        @click="onScopeChipClick"
      >
        {{ t('scope.chip', { scope }) }}
      </Badge>
      <Button type="submit" size="sm" class="ml-auto" :disabled="busy || !draft.trim()">
        {{ busy ? t('chat.sending') : t('chat.send') }}
      </Button>
    </div>
  </form>
</template>
