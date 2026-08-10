<script setup lang="ts">
/**
 * One exchange: the question, what the assistant did about it, and the answer.
 *
 * The middle part is not decoration. "reading device:D03.XCBR1" is the honest
 * account of the work — a spinner in its place is where a system stops being
 * inspectable, and this product's entire claim is that an operator can check
 * what it did (ADR-0004). The tool trace stays on screen after the answer
 * arrives for the same reason.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Exchange } from '@/stores/chat'
import ErrorBox from '@/ui/ErrorBox.vue'
import TurnAnswer from './TurnAnswer.vue'

const props = defineProps<{ turn: Exchange }>()
const emit = defineEmits<{ retry: [] }>()

const { t, d } = useI18n()

/**
 * A reopened turn says when it was asked and that its evidence is not here.
 *
 * Saying it is the whole point. Stored turns carry words and no readings by
 * design (ADR-0022 §2); a turn that simply rendered without its evidence block
 * would read as one whose evidence went missing, which is a bug report waiting
 * to happen and, worse, teaches people that a missing evidence block is normal.
 */
const askedAt = computed(() => {
  if (!props.turn.historical || !props.turn.askedAt) return ''
  const at = new Date(props.turn.askedAt)
  return Number.isNaN(at.getTime()) ? '' : d(at, 'full')
})

/** What the assistant decided the question was about, once it has decided. */
const scope = computed(
  () => props.turn.answer?.scope ?? props.turn.summary?.scope ?? props.turn.askedFrom,
)

const trace = computed(() => props.turn.tools.join(' → '))
const showTrace = computed(() => Boolean(trace.value))
</script>

<template>
  <article class="flex flex-col gap-3 border-b border-border px-4 py-4 last:border-b-0">
    <div class="flex flex-col items-end gap-1">
      <p
        class="m-0 max-w-full rounded-lg bg-secondary px-3 py-2 text-sm leading-relaxed text-secondary-foreground"
      >
        {{ turn.question }}
      </p>
      <p class="m-0 font-mono text-2xs text-sys-idle">
        {{ t('chat.about', { scope }) }}
      </p>
    </div>

    <p
      v-if="showTrace"
      class="m-0 rounded-md bg-muted/35 px-2 py-1 font-mono text-2xs text-muted-foreground"
    >
      {{ trace }}
    </p>

    <p v-if="turn.historical" class="m-0 text-2xs text-sys-warn">
      {{ t('chat.historical', { at: askedAt }) }}
    </p>

    <ErrorBox
      v-if="turn.error"
      :code="turn.error.code"
      :message="turn.error.message"
      class="items-start text-left"
      @retry="emit('retry')"
    />

    <TurnAnswer v-else :turn="turn" />
  </article>
</template>
