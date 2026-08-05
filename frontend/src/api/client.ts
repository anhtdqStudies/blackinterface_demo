/**
 * The only place that talks HTTP.
 *
 * Every type here comes from `schema.d.ts`, which is generated from the
 * backend's OpenAPI document (ADR-0009). Rename a field in FastAPI and this
 * file stops compiling — which is the point. Do not hand-write API types.
 */
import type { components } from './schema'

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
export type Issue = components['schemas']['ValidationIssue']
export type SwitchState = components['schemas']['SwitchState']
export type Quality = components['schemas']['Quality']
/** Which conductors are live, solved in the backend. Never recomputed here. */
export type Energization = components['schemas']['EnergizationOut']
export type Island = components['schemas']['Island']
export type LiveState = components['schemas']['LiveState']
export type CrossCheck = components['schemas']['CrossCheck']
/** Everything about the station that moves. What `/api/stream` pushes. */
export type Live = components['schemas']['LiveOut']
export type DeviceLive = components['schemas']['DeviceLiveOut']
/** The state of the subscription itself — not of the station. */
export type Link = components['schemas']['LinkOut']

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
  health: () => request<Health>('/api/health'),
  station: () => request<Station>('/api/station'),
  bays: () => request<Bay[]>('/api/bays'),
  bay: (id: string) => request<BayDetail>(`/api/bays/${encodeURIComponent(id)}`),
  busbars: () => request<Busbar[]>('/api/busbars'),
  /** The whole station, all voltage levels stacked. */
  stationDiagram: () => request<StationDiagram>('/api/diagram'),
  /** Which sections are live, keyed by connectivity node. Joins onto the
   *  diagram through `RailView.node_id` / `EdgeView.node_id`. */
  energization: () => request<Energization>('/api/energization'),
  /** One poll of the live document. The stream pushes this same shape, so
   *  there is a single code path applying it — see stores/station.ts. */
  live: () => request<Live>('/api/live'),
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
