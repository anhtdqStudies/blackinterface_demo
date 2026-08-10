<script setup lang="ts">
/**
 * Asking the station a question in words (ADR-0019).
 *
 * The pane follows the workspace scope rather than taking one as a prop for the
 * usual reason (ADR-0010): the scope sent with each question is what "còn số đo
 * thì sao?" resolves against, and it must be the bay the operator is actually
 * looking at — not a copy this component made when it mounted.
 *
 * The transcript lives in the store, not here — layout is fixed (ADR-0018) so
 * the chat column does not remount when the operator switches workspace tabs.
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import type { PaneProps } from '@/app/layout/panes'
import { formatScope } from '@/scope'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useWorkspaceStore } from '@/stores/workspace'
import Empty from '@/ui/Empty.vue'
import { Button } from '@/ui/button'
import AskBox from './AskBox.vue'
import ConversationMenu from './ConversationMenu.vue'
import TurnBlock from './TurnBlock.vue'

defineProps<PaneProps>()

const { t } = useI18n()
const chat = useChatStore()
const session = useSessionStore()
const workspace = useWorkspaceStore()

/**
 * Hidden rather than merely refused. An account without `agent.ask` should not
 * be shown a composer that answers every question with a permission error
 * (ADR-0016 §4: the interface hides what the caller cannot use).
 */
const allowed = computed(() => session.can('agent.ask'))

const scope = computed(() => formatScope(workspace.scope))

/**
 * Which model, or none. Read from the last answer rather than from config,
 * because config is what we asked for and this is what actually happened — and
 * on a station those differ exactly when it matters (ADR-0019 §3).
 */
const provider = computed(() => {
  for (let i = chat.turns.length - 1; i >= 0; i -= 1) {
    const answer = chat.turns[i]?.answer
    if (answer) return answer
  }
  return null
})

const transcript = ref<HTMLElement | null>(null)

/** The store owns the failure; nothing here has to await the answer. */
function ask(question: string): void {
  void chat.ask(question)
}

function retry(): void {
  void chat.retry()
}

/**
 * Load the thread list once the pane appears.
 *
 * Not in the store's setup: this pane mounts once per session layout. Cheap to
 * repeat on remount because the list is a handful of rows.
 */
onMounted(() => {
  if (allowed.value) void chat.refresh()
})

/** Keep the newest turn in view, including while prose is still arriving. */
watch(
  () =>
    chat.turns
      .map(
        (turn) =>
          `${turn.text.length}.${turn.reading.length}.${turn.summary ? 1 : 0}.${turn.pending ? 1 : 0}`,
      )
      .join(','),
  async () => {
    await nextTick()
    const box = transcript.value
    if (box) box.scrollTop = box.scrollHeight
  },
)
</script>

<template>
  <Empty v-if="!allowed" :reason="t('chat.notAllowed')" />

  <div v-else class="flex h-full min-h-0 flex-col">
    <div
      class="flex shrink-0 items-center gap-2 border-b border-border px-2 py-1.5 text-2xs text-sys-idle"
    >
      <ConversationMenu />
      <Button
        variant="ghost"
        size="icon-xs"
        :title="workspace.chatCollapsed ? t('chat.expand') : t('chat.collapse')"
        @click="workspace.toggleChatCollapsed()"
      >
        <PanelLeftOpen v-if="workspace.chatCollapsed" />
        <PanelLeftClose v-else />
      </Button>
      <span v-if="provider" class="ml-auto truncate">
        {{
          provider.generated
            ? t('chat.model', { provider: provider.provider })
            : t('chat.noModel')
        }}
      </span>
    </div>

    <div ref="transcript" class="min-h-0 flex-1 overflow-auto bg-muted/20">
      <Empty v-if="!chat.turns.length" :reason="t('chat.empty')" />
      <TurnBlock v-for="turn in chat.turns" :key="turn.id" :turn="turn" @retry="retry" />
    </div>

    <AskBox :busy="chat.busy" :scope="scope" @ask="ask" />
  </div>
</template>
