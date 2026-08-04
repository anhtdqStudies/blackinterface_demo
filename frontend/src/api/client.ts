/**
 * The only place that talks HTTP.
 *
 * Every type here comes from `schema.d.ts`, which is generated from the
 * backend's OpenAPI document (ADR-0009). Rename a field in FastAPI and this
 * file stops compiling — which is the point. Do not hand-write API types.
 */
import type { components } from './schema'

export type Health = components['schemas']['HealthOut']
export type Station = components['schemas']['StationOut']
export type Bay = components['schemas']['BayOut']
export type BayDetail = components['schemas']['BayDetailOut']
export type Device = components['schemas']['DeviceOut']
export type Busbar = components['schemas']['BusbarOut']
export type Diagram = components['schemas']['DiagramView']
export type Symbol_ = components['schemas']['SymbolView']
export type Rail = components['schemas']['RailView']
export type Edge = components['schemas']['EdgeView']
export type Column = components['schemas']['ColumnView']
export type Terminal = components['schemas']['TerminalView']
export type Issue = components['schemas']['ValidationIssue']
export type SwitchState = components['schemas']['SwitchState']
export type Quality = components['schemas']['Quality']

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
  diagram: (voltageLevel: string) =>
    request<Diagram>(`/api/diagram/${encodeURIComponent(voltageLevel)}`),
  /** Re-read the source. Writes nothing to OneATS (AGENTS.md I1). */
  reload: () => request<Health>('/api/reload', { method: 'POST' }),
}
