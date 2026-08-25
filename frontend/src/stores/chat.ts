/**
 * The conversation on screen, and the threads behind it (ADR-0018, ADR-0022).
 *
 * A store rather than a component ref because the chat pane is unmounted and
 * remounted every time somebody changes layout, and a thread that resets on a
 * layout change is not a thread.
 *
 * Threads live in the backend's SQLite now, so this store no longer has to
 * pretend the id it holds is the whole of the memory: it lists them, reopens
 * them, and throws them away. What it must never do is *reconstruct* one. Which
 * turns a model is told about is the backend's decision (ADR-0022 §1) and is not
 * derivable from what happens to be rendered here.
 *
 * **Facts and prose are kept apart, and stay apart** (I3). `text` is what a model
 * wrote; `summary` / `resolution` arrive from tools before `answer` closes the
 * turn. This store never merges them into one string, because once merged
 * nothing downstream can tell which half was measured.
 *
 * **A reopened turn has no evidence, and that is not a loss.** The backend
 * stores words, never readings: an evidence record describes one moment, and
 * showing it again days later would put a stale number on screen looking exactly
 * like a live one. Reopened turns carry `historical: true` so the interface can
 * say so rather than render a turn that looks like its evidence went missing.
 */
import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import {
  ApiError,
  api,
  type Answer,
  type Conversation,
  type ConversationTurn,
  type Evidence,
  type Resolve,
  type Summary,
  type ToolCall,
} from '@/api/client'
import { formatScope } from '@/scope'
import { useWorkspaceStore } from '@/stores/workspace'

/** One exchange: what was asked, what happened, what came back. */
export interface Exchange {
  /** Local id. Replaced by the backend's `turn_id` as soon as it arrives. */
  id: string
  question: string
  /** The scope the question was asked *from* — the fallback subject (AskIn). */
  askedFrom: string
  /** Tool names in call order. The honest account of what the assistant did. */
  tools: string[]
  /** Tool about to run — drives the status line until it finishes. */
  pendingTool: ToolCall | null
  /** Structured payloads as they stream in, before the final answer frame. */
  resolution: Resolve | null
  summary: Summary | null
  /** Evidence as it streams in, before the final answer carries the full list. */
  reading: Evidence[]
  /** Prose accumulated from `token` frames. Superseded by `answer.text`. */
  text: string
  answer: Answer | null
  error: ApiError | null
  /** True until the stream ends, whether it ended well or not. */
  pending: boolean
  /**
   * Read back from a stored transcript rather than watched happening. Carries
   * no evidence and never will — see the module docstring.
   */
  historical: boolean
  /** ISO time, set only on historical turns; live ones are happening now. */
  askedAt: string
}

let counter = 0

function newExchange(question: string, askedFrom: string): Exchange {
  counter += 1
  return reactive({
    id: `local-${counter}`,
    question,
    askedFrom,
    tools: [],
    pendingTool: null,
    resolution: null,
    summary: null,
    reading: [],
    text: '',
    answer: null,
    error: null,
    pending: true,
    historical: false,
    askedAt: '',
  }) as Exchange
}

/** A turn as it was stored: the question, the prose, and when. Nothing measured. */
function storedExchange(turn: ConversationTurn): Exchange {
  return reactive({
    id: turn.turn_id,
    question: turn.question,
    askedFrom: turn.scope || turn.asked_from,
    tools: [],
    pendingTool: null,
    resolution: null,
    summary: null,
    reading: [],
    text: turn.answer,
    answer: null,
    error: null,
    pending: false,
    historical: true,
    askedAt: turn.asked_at,
  }) as Exchange
}

export const useChatStore = defineStore('chat', () => {
  const turns = ref<Exchange[]>([])
  /** The backend's thread id. Null until the first answer names one. */
  const conversationId = ref<string | null>(null)
  const busy = ref(false)
  /** Every thread this account has, newest first. Empty until `refresh()`. */
  const conversations = ref<Conversation[]>([])
  /** Set when listing or reopening fails; asking has its own per-turn error. */
  const listError = ref<ApiError | null>(null)

  /** Cancels the stream in flight, so leaving the screen does not leave a socket. */
  let inFlight: AbortController | null = null

  /**
   * Ask one question.
   *
   * The scope is read here rather than taken as an argument because it must be
   * the scope the operator is actually looking at — "còn số đo thì sao?" means
   * *this* bay, and the workspace store is the only thing that knows which one
   * (ADR-0010). A component passing its own copy is how the two drift.
   */
  async function ask(question: string): Promise<void> {
    const text = question.trim()
    if (!text || busy.value) return

    const askedFrom = formatScope(useWorkspaceStore().scope)
    const turn = newExchange(text, askedFrom)
    turns.value.push(turn)
    busy.value = true

    const controller = new AbortController()
    inFlight = controller

    try {
      await api.askStream(
        { question: text, scope: askedFrom, conversation_id: conversationId.value },
        {
          turn: (frame) => {
            turn.id = frame.turn_id
            conversationId.value = frame.conversation_id
          },
          tool: (frame) => {
            turn.tools.push(frame.tool)
            turn.pendingTool = frame
          },
          evidence: (frame) => turn.reading.push(frame),
          resolution: (frame) => {
            turn.resolution = frame
            turn.pendingTool = null
          },
          summary: (frame) => {
            turn.summary = frame
            turn.pendingTool = null
          },
          token: (piece) => {
            turn.text += piece
          },
          answer: (frame) => {
            turn.answer = frame
            turn.text = frame.text
            if (frame.resolution) turn.resolution = frame.resolution
            if (frame.summary) turn.summary = frame.summary
          },
        },
        controller.signal,
      )
      if (!turn.answer && !controller.signal.aborted) {
        turn.error = new ApiError('stream_truncated', 'Luồng trả lời bị cắt giữa chừng', 0)
      }
    } catch (cause) {
      if (controller.signal.aborted) return
      turn.error = cause instanceof ApiError ? cause : new ApiError('unknown', String(cause), 0)
    } finally {
      turn.pending = false
      turn.pendingTool = null
      if (inFlight === controller) {
        inFlight = null
        busy.value = false
      }
      // The title and the ordering both change on the first turn of a thread.
      // Refreshing after every answer costs one small request and keeps the
      // picker from showing a thread under a title it has outgrown.
      void refresh()
    }
  }

  /** Re-ask the last question. What a failed turn's retry button does. */
  async function retry(): Promise<void> {
    const last = turns.value[turns.value.length - 1]
    if (!last || busy.value || last.historical) return
    turns.value.pop()
    await ask(last.question)
  }

  /** Start a fresh thread. The backend opens one on the next question. */
  function reset(): void {
    inFlight?.abort()
    inFlight = null
    busy.value = false
    turns.value = []
    conversationId.value = null
    listError.value = null
  }

  /** Load the thread list. Safe to call often; failures are shown, not thrown. */
  async function refresh(): Promise<void> {
    try {
      conversations.value = await api.conversations()
    } catch (cause) {
      if (cause instanceof ApiError) listError.value = cause
    }
  }

  /**
   * Reopen a stored thread.
   *
   * Replaces the transcript on screen wholesale rather than merging: a thread is
   * the unit the backend remembers, and half of one plus half of another is a
   * screen whose follow-up questions mean something different from what it shows.
   */
  async function open(id: string): Promise<void> {
    if (busy.value || id === conversationId.value) return
    inFlight?.abort()
    inFlight = null
    try {
      const found = await api.conversation(id)
      turns.value = found.transcript.map(storedExchange)
      conversationId.value = found.id
      listError.value = null
    } catch (cause) {
      if (cause instanceof ApiError) listError.value = cause
    }
  }

  /** Forget a thread. Clears the screen too when it was the one open. */
  async function remove(id: string): Promise<void> {
    try {
      conversations.value = await api.deleteConversation(id)
      if (id === conversationId.value) reset()
    } catch (cause) {
      if (cause instanceof ApiError) listError.value = cause
    }
  }

  return {
    turns,
    conversationId,
    conversations,
    listError,
    busy,
    ask,
    retry,
    reset,
    refresh,
    open,
    remove,
  }
})
