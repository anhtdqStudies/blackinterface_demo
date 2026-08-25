/**
 * The only place that talks HTTP.
 *
 * Every type here comes from `schema.d.ts`, which is generated from the
 * backend's OpenAPI document (ADR-0009). Rename a field in FastAPI and this
 * file stops compiling — which is the point. Do not hand-write API types.
 */
import type { components } from './schema'

/** Who is calling and what they may do (ADR-0016). */
export type Me = components['schemas']['MeOut']
export type Health = components['schemas']['HealthOut']
export type Project = components['schemas']['ProjectOut']
export type ProjectLoad = components['schemas']['ProjectLoadOut']
export type Station = components['schemas']['StationOut']
export type Bay = components['schemas']['BayOut']
export type BayDetail = components['schemas']['BayDetailOut']
export type Device = components['schemas']['DeviceOut']
export type Busbar = components['schemas']['BusbarOut']
export type Diagram = components['schemas']['DiagramView']
/** Every voltage level in one drawing. What the SLD view renders. */
export type StationDiagram = components['schemas']['StationView']
export type Section = components['schemas']['SectionView']
export type Symbol_ = components['schemas']['SymbolView']
export type Rail = components['schemas']['RailView']
export type Edge = components['schemas']['EdgeView']
export type Column = components['schemas']['ColumnView']
export type Terminal = components['schemas']['TerminalView']
export type Junction = components['schemas']['JunctionView']
export type Issue = components['schemas']['ValidationIssueOut']
export type IssueGroup = Issue['group']
export type Issues = components['schemas']['IssuesOut']
export type SwitchState = components['schemas']['SwitchState']
export type Quality = components['schemas']['Quality']
/** Which conductors are live, solved in the backend. Never recomputed here. */
export type Energization = components['schemas']['EnergizationOut']
export type Island = components['schemas']['Island']
export type LiveState = components['schemas']['LiveState']
export type CrossCheck = components['schemas']['CrossCheck']
/** All three cadences at once. What `/api/live` returns on the first load. */
export type Live = components['schemas']['LiveOut']
/** What the station *is*: positions, IsLive, energisation. SSE event `state`. */
export type State = components['schemas']['StateOut']
/** What the station is *reading*. SSE event `measurement`. */
export type Measurement = components['schemas']['MeasurementOut']
export type Reading = components['schemas']['ReadingOut']
export type Quantity = components['schemas']['Quantity']
export type Unit = components['schemas']['Unit']
export type DeviceLive = components['schemas']['DeviceLiveOut']
/** The state of the subscription itself — not of the station. SSE event `link`. */
export type Link = components['schemas']['LinkOut']
/** How one scope is doing, with the evidence behind the answer. */
export type Summary = components['schemas']['SummaryOut']

// Module B — alarms and incidents (ADR-0026 channels, ADR-0027 model).
/** One alarm, already classified: `klass` is what the pane filters on. */
export type Alarm = components['schemas']['AlarmOut']
export type Alarms = components['schemas']['AlarmsOut']
/** A cluster of alarms that belong together in time and in the network. */
export type Incident = components['schemas']['IncidentOut']
export type Incidents = components['schemas']['IncidentsOut']
/** Handling guidance. `status` says whether anybody has approved it. */
export type Playbook = components['schemas']['PlaybookOut']
export type PlaybookStep = components['schemas']['PlaybookStepOut']
/** The `alarm` cadence on the shared stream. */
export type AlarmLive = components['schemas']['AlarmLiveOut']
export type Evidence = components['schemas']['EvidenceRecord']
export type Limit = components['schemas']['Limit']
export type LimitCode = components['schemas']['LimitCode']
export type Coverage = components['schemas']['Coverage']
export type PointQuality = components['schemas']['PointQ']

/** A question, and the scope the person was looking at when they asked it. */
export type Ask = components['schemas']['AskIn']
/** One turn of conversation: prose, computed statement, and what it rests on. */
export type Answer = components['schemas']['AnswerOut']
/** What a name refers to. `scope` is set only when exactly one thing matched. */
export type Resolve = components['schemas']['ResolveOut']
export type ScopeCandidate = components['schemas']['ScopeCandidateOut']
/** First streamed frame: the turn exists, and whether a model is involved. */
export type TurnStart = components['schemas']['TurnStartOut']
/** A tool about to run. Announced, not merely logged — see agent.py. */
export type ToolCall = components['schemas']['ToolCallOut']
/** A thread in the picker: title, times, length. No transcript (ADR-0022). */
export type Conversation = components['schemas']['ConversationOut']
/** One thread reopened, with what was said in it. */
export type ConversationDetail = components['schemas']['ConversationDetailOut']
/**
 * One remembered turn — **words, not readings**.
 *
 * There is no evidence and no summary on this type, and that is the backend
 * saying so rather than something omitted here. An evidence record describes one
 * moment; re-rendering it days later next to a question would put a stale number
 * on screen looking exactly like a live one (ADR-0022 §2). A reopened transcript
 * shows what was said; current figures come from asking again.
 */
export type ConversationTurn = components['schemas']['ConversationTurnOut']
/** Which model this installation uses. **Never carries the API key.** */
export type AssistantConfig = components['schemas']['AssistantConfigOut']
export type AssistantConfigInput = components['schemas']['AssistantConfigIn']
/** The result of actually calling the model, not of validating the form. */
export type AssistantProbe = components['schemas']['AssistantProbeOut']

/** The backend's uniform error body. See backend/src/blackinterface/errors.py. */
interface ErrorBody {
  error: { code: string; message: string; detail: Record<string, unknown> }
}

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly detail: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** The error a non-2xx response stands for. Reads the body when it has one. */
async function failure(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => null)) as ErrorBody | null
  if (body?.error) {
    return new ApiError(body.error.code, body.error.message, response.status, body.error.detail)
  }
  return new ApiError(
    'http_error',
    `${response.status} ${response.statusText}`,
    response.status,
  )
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch (cause) {
    // Network-level failure: the API process is down or unreachable. Worth
    // distinguishing from an API error, because the fix is different.
    throw new ApiError('unreachable', `Không gọi được ${path}`, 0, { cause: String(cause) })
  }
  if (!response.ok) throw await failure(response)
  return response
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await send(path, init)).json() as Promise<T>
}

function posting(body: unknown, signal?: AbortSignal): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  }
}

/**
 * What a caller wants to hear about while an answer is being produced.
 *
 * Every handler is optional and every one of them is also redundant: the final
 * `answer` frame carries the complete `AnswerOut`, so a client that only
 * implements `answer` gets exactly what `POST /api/ask` would have returned.
 * The rest exist so the screen can show the work happening (agent.py, ADR-0019 §7).
 */
export interface AskFrames {
  turn?: (frame: TurnStart) => void
  tool?: (frame: ToolCall) => void
  evidence?: (frame: Evidence) => void
  /** Structured resolve payload, before the model finishes writing. */
  resolution?: (frame: Resolve) => void
  /** Structured summary payload — the measured statement can render immediately. */
  summary?: (frame: Summary) => void
  /** A fragment of prose. Never the whole of `AnswerOut.text`. */
  token?: (text: string) => void
  answer?: (frame: Answer) => void
}

/** Split an SSE buffer into complete frames, returning the unterminated tail. */
function frames(buffer: string): { done: string[]; rest: string } {
  const parts = buffer.split('\n\n')
  return { done: parts.slice(0, -1), rest: parts[parts.length - 1] ?? '' }
}

/**
 * Dispatch one `event:`/`data:` frame. Unknown event names are ignored rather
 * than thrown on — a newer backend must be able to add a frame type without
 * breaking a browser that has an older bundle cached.
 */
function dispatch(frame: string, on: AskFrames): void {
  let name = ''
  const data: string[] = []
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) name = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).trim())
  }
  if (!name || !data.length) return
  const payload: unknown = JSON.parse(data.join('\n'))
  switch (name) {
    case 'turn':
      on.turn?.(payload as TurnStart)
      return
    case 'tool':
      on.tool?.(payload as ToolCall)
      return
    case 'evidence':
      on.evidence?.(payload as Evidence)
      return
    case 'resolution':
      on.resolution?.(payload as Resolve)
      return
    case 'summary':
      on.summary?.(payload as Summary)
      return
    case 'token':
      on.token?.((payload as { text: string }).text)
      return
    case 'answer':
      on.answer?.(payload as Answer)
  }
}

export const api = {
  // Identity (ADR-0017). The session lives in an HttpOnly cookie, so none of
  // these hand a token back — there is nothing here for the frontend to hold,
  // and that is deliberate: what JavaScript cannot read, an XSS cannot steal.
  /** The caller's identity and permissions. Read once, before the first route. */
  me: () => request<Me>('/api/me'),
  login: (username: string, password: string) =>
    request<Me>('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<Me>('/api/logout', { method: 'POST' }),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<Me>('/api/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  health: () => request<Health>('/api/health'),
  station: () => request<Station>('/api/station'),
  issues: () => request<Issues>('/api/issues'),
  bays: () => request<Bay[]>('/api/bays'),
  bay: (id: string) => request<BayDetail>(`/api/bays/${encodeURIComponent(id)}`),
  busbars: () => request<Busbar[]>('/api/busbars'),
  /** The whole station, all voltage levels stacked. */
  stationDiagram: () => request<StationDiagram>('/api/diagram'),
  /** Which sections are live, keyed by connectivity node. Joins onto the
   *  diagram through `RailView.node_id` / `EdgeView.node_id`. */
  energization: () => request<Energization>('/api/energization'),
  /** One poll of all three cadences. The stream pushes each of them under the
   *  same schema, so there is one code path per cadence — see stores/stream.ts. */
  live: () => request<Live>('/api/live'),
  /** How one scope is doing, with the evidence behind it (ADR-0013). */
  summary: (scope: string) =>
    request<Summary>(`/api/summary?scope=${encodeURIComponent(scope)}`),
  /**
   * Active alarms for one scope.
   *
   * Switch positions are excluded unless asked for: a healthy station
   * annunciates 90 of them and they are evidence, not faults (ADR-0027).
   */
  alarms: (scope: string, includeStatus = false) =>
    request<Alarms>(
      `/api/alarms?scope=${encodeURIComponent(scope)}` +
        (includeStatus ? '&include_status=true' : ''),
    ),
  /** Alarms grouped into incidents, each carrying its handling guidance. */
  incidents: (scope: string, status: 'open' | 'dismissed' = 'open') =>
    request<Incidents>(`/api/incidents?scope=${encodeURIComponent(scope)}&status=${status}`),
  /** Mark one open incident as handled locally — not OneATS acknowledgement (I1). */
  dismissIncident: (incidentId: string, scope: string) =>
    request<Incident>(
      `/api/incidents/${encodeURIComponent(incidentId)}/dismiss?scope=${encodeURIComponent(scope)}`,
      { method: 'POST' },
    ),
  /** One voltage level on its own. Kept for tooling and manual inspection. */
  diagram: (voltageLevel: string) =>
    request<Diagram>(`/api/diagram/${encodeURIComponent(voltageLevel)}`),
  /** Re-read the source. Writes nothing to OneATS (AGENTS.md I1). */
  reload: () => request<Health>('/api/reload', { method: 'POST' }),

  // Which model the assistant uses. The key travels one way only — it goes up
  // in `saveAssistant` and never comes back down; `AssistantConfig` says
  // whether one is stored and nothing more.
  assistant: () => request<AssistantConfig>('/api/assistant/config'),
  saveAssistant: (body: AssistantConfigInput) =>
    request<AssistantConfig>('/api/assistant/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  /** Call the model for real. The only thing that can set `verified_at`. */
  testAssistant: () => request<AssistantProbe>('/api/assistant/test', { method: 'POST' }),

  // The assistant (ADR-0019). POST for both, including the stream: a question is
  // free text and belongs in a body, not in a URL that lands in the proxy's
  // access log and in the control-room browser's history.
  /** Ask and wait. The whole answer at once. */
  ask: (body: Ask) => request<Answer>('/api/ask', posting(body)),
  /**
   * Ask and watch. Resolves when the stream ends; the final `answer` frame is
   * the authority and replaces anything accumulated from `token` (ADR-0019 §6).
   */
  askStream: async (body: Ask, on: AskFrames, signal?: AbortSignal): Promise<void> => {
    const response = await send('/api/ask/stream', posting(body, signal))
    const stream = response.body
    if (!stream) throw new ApiError('unreachable', 'Không đọc được stream', 0)
    const reader = stream.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''
    try {
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += value
        const split = frames(buffer)
        buffer = split.rest
        for (const frame of split.done) dispatch(frame, on)
      }
      // A stream cut without the trailing blank line still carries a last frame.
      if (buffer.trim()) dispatch(buffer, on)
    } finally {
      reader.releaseLock()
    }
  },

  // Conversations (ADR-0022). Threads belong to the account that opened them;
  // one that is not yours is a 404, never a 403, so an id nobody should have
  // learns nothing from asking.
  /** The caller's own threads, most recent first. */
  conversations: () => request<Conversation[]>('/api/conversations'),
  /** One thread and its transcript. Words only — see `ConversationTurn`. */
  conversation: (id: string) =>
    request<ConversationDetail>(`/api/conversations/${encodeURIComponent(id)}`),
  /** Forget a thread. Returns the ones left, so the picker needs no reload. */
  deleteConversation: (id: string) =>
    request<Conversation[]>(`/api/conversations/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),

  // Projects — named DataServer connections plus their snapshots. Every call
  // below writes only to the local SQLite store, never to OneATS (I1).
  projects: () => request<Project[]>('/api/projects'),
  /** Create a project and immediately browse its DataServer. */
  createProject: (name: string, opcuaUrl: string) =>
    request<ProjectLoad>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, opcua_url: opcuaUrl }),
    }),
  /** Make a project current; renders from its snapshot when one exists. */
  openProject: (id: number) =>
    request<ProjectLoad>(`/api/projects/${id}/open`, { method: 'POST' }),
  /** Browse the project's DataServer live and replace its snapshot. */
  refreshProject: (id: number) =>
    request<ProjectLoad>(`/api/projects/${id}/refresh`, { method: 'POST' }),
  /** Remove a project and its snapshot. Returns the remaining projects. */
  deleteProject: (id: number) =>
    request<Project[]>(`/api/projects/${id}`, { method: 'DELETE' }),
}
