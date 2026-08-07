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
export type Evidence = components['schemas']['EvidenceRecord']
export type Limit = components['schemas']['Limit']
export type LimitCode = components['schemas']['LimitCode']
export type Coverage = components['schemas']['Coverage']
export type PointQuality = components['schemas']['PointQ']

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch (cause) {
    // Network-level failure: the API process is down or unreachable. Worth
    // distinguishing from an API error, because the fix is different.
    throw new ApiError('unreachable', `Không gọi được ${path}`, 0, { cause: String(cause) })
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null
    if (body?.error) {
      throw new ApiError(
        body.error.code,
        body.error.message,
        response.status,
        body.error.detail,
      )
    }
    throw new ApiError(
      'http_error',
      `${response.status} ${response.statusText}`,
      response.status,
    )
  }
  return (await response.json()) as T
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
  /** One voltage level on its own. Kept for tooling and manual inspection. */
  diagram: (voltageLevel: string) =>
    request<Diagram>(`/api/diagram/${encodeURIComponent(voltageLevel)}`),
  /** Re-read the source. Writes nothing to OneATS (AGENTS.md I1). */
  reload: () => request<Health>('/api/reload', { method: 'POST' }),

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
