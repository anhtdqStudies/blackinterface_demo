<script setup lang="ts">
/**
 * Picking a thread, starting one, throwing one away (ADR-0022 §3).
 *
 * A menu rather than a sidebar. The chat pane is one cell of a workspace that
 * also has to show a diagram and a state table, and a permanent thread list
 * would spend the scarcest thing on the screen — width — on something an
 * operator touches a few times a shift.
 *
 * Titles are the operator's own first question. That is why nothing here
 * truncates them harder than the backend already did: a thread is found again
 * by recognising the words somebody typed.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MessageSquarePlus, MessagesSquare, Trash2 } from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import { Button } from '@/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/ui/dropdown-menu'

const { t, d } = useI18n()
const chat = useChatStore()

const current = computed(() => chat.conversations.find((c) => c.id === chat.conversationId))

/** The label on the trigger: this thread's title, or an invitation to start one. */
const label = computed(() => current.value?.title || t('chat.threads.untitled'))

/** `full` rather than a relative label: see the note on TIME in `i18n/index.ts`. */
function when(iso: string): string {
  const at = new Date(iso)
  return Number.isNaN(at.getTime()) ? '' : d(at, 'full')
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" size="xs" class="max-w-56 gap-1.5">
        <MessagesSquare />
        <span class="truncate">{{ label }}</span>
      </Button>
    </DropdownMenuTrigger>

    <DropdownMenuContent align="start" class="w-80">
      <DropdownMenuItem @select="chat.reset()">
        <MessageSquarePlus />
        {{ t('chat.threads.new') }}
      </DropdownMenuItem>

      <DropdownMenuSeparator />
      <DropdownMenuLabel class="text-2xs text-sys-idle">
        {{ t('chat.threads.recent') }}
      </DropdownMenuLabel>

      <p v-if="!chat.conversations.length" class="px-2 py-1.5 text-xs text-muted-foreground">
        {{ t('chat.threads.none') }}
      </p>

      <DropdownMenuItem
        v-for="thread in chat.conversations"
        :key="thread.id"
        class="items-start gap-2"
        :data-active="thread.id === chat.conversationId ? '' : undefined"
        @select="chat.open(thread.id)"
      >
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-xs text-foreground">{{ thread.title }}</span>
          <span class="text-2xs text-sys-idle">
            {{ when(thread.last_at) }} · {{ t('chat.threads.turns', thread.turns) }}
          </span>
        </span>
        <!-- `.stop` so removing a thread does not also open it on the way out. -->
        <Button
          variant="ghost"
          size="icon-xs"
          :aria-label="t('chat.threads.delete')"
          :title="t('chat.threads.delete')"
          @click.stop.prevent="chat.remove(thread.id)"
        >
          <Trash2 />
        </Button>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
