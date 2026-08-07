<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isPinned, PANE_TITLE_KEY, type Pane } from './panes'
import { formatScope, type ScopeRef } from '@/scope'
import Badge from '@/ui/Badge.vue'

/**
 * The chrome around one pane: a title, and — when it matters — the fact that
 * this cell is **not** following the rest of the screen.
 *
 * Kept out of the pane components so eleven of them do not each grow their own
 * heading, which is precisely how the copy-pasted `h2` blocks that ADR-0014 §1
 * measured came about.
 */
const props = defineProps<{ pane: Pane; scope: ScopeRef }>()

const { t } = useI18n()

const title = computed(() => t(PANE_TITLE_KEY[props.pane.kind]))

/**
 * A pinned pane has to announce itself. Without the badge, an operator who
 * clicked a bay sees one cell still describing the previous one and has no way
 * to know that was asked for — the pin stops being a feature and becomes a
 * screen that quietly disagrees with itself.
 */
const pin = computed(() => (isPinned(props.pane) ? formatScope(props.scope) : null))

/** Inspector carries its own scope header — skip the duplicate uppercase bar. */
const minimalChrome = computed(() => props.pane.params?.chrome === 'minimal')
</script>

<template>
  <section class="flex h-full min-h-0 min-w-0 flex-col bg-panel">
    <header
      v-if="!minimalChrome"
      class="flex shrink-0 items-center gap-2 border-b border-line px-3 py-[6px] text-xs font-semibold tracking-[0.08em] text-dim uppercase"
    >
      {{ title }}
      <Badge v-if="pin" tone="warn" :title="t('pane.pinnedHint')">
        {{ t('pane.pinned', { scope: pin }) }}
      </Badge>
    </header>

    <div class="min-h-0 flex-1 overflow-auto">
      <slot />
    </div>
  </section>
</template>
