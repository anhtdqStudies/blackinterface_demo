/**
 * Scope references — the frontend half of `backend/src/blackinterface/domain/scope.py`.
 *
 * The same string appears in the URL, in a pane's key, in a tool argument and in
 * an evidence subject (ADR-0010, AGENTS.md I8). This module is the only place in
 * the frontend that produces or reads the format; nowhere else may write
 * `` `bay:${id}` ``.
 *
 * Two implementations of one grammar is a duplication worth naming. The
 * alternative — shipping scope refs as structured JSON so the type could be
 * generated from OpenAPI — would put braces in every URL and every pane key.
 * The mitigation is that the grammar is tiny, frozen, and asserted on both
 * sides: `tests/unit/test_scope.py` and the parse table below stay in step
 * because the kinds are enumerated in one visible place in each.
 */

export const SCOPE_KINDS = [
  'station',
  'vl',
  'transformer',
  'busbar',
  'bay',
  'device',
  'point',
] as const

export type ScopeKind = (typeof SCOPE_KINDS)[number]

export interface ScopeRef {
  readonly kind: ScopeKind
  readonly id: string
}

/** Only the station has no id — there is exactly one of it. */
const NO_ID: readonly ScopeKind[] = ['station']

/** Matches `domain/scope.py`: letters, digits, dot, dash, underscore. */
const ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/

const SEP = ':'

export const STATION: ScopeRef = { kind: 'station', id: '' }

export function scope(kind: ScopeKind, id = ''): ScopeRef {
  return { kind, id }
}

export const bay = (id: string): ScopeRef => scope('bay', id)
export const device = (id: string): ScopeRef => scope('device', id)
export const busbar = (id: string): ScopeRef => scope('busbar', id)
export const transformer = (id: string): ScopeRef => scope('transformer', id)
export const voltageLevel = (id: string): ScopeRef => scope('vl', id)
export const point = (id: string): ScopeRef => scope('point', id)

/** The canonical string. The only place this format is produced. */
export function formatScope(ref: ScopeRef): string {
  return NO_ID.includes(ref.kind) ? ref.kind : `${ref.kind}${SEP}${ref.id}`
}

/**
 * Read a scope ref, or `null` if it is not one.
 *
 * Returns null rather than falling back to the station. A URL that no longer
 * parses is a bug or a stale bookmark; answering it about the whole station
 * would silently widen what the operator asked for, and nothing downstream
 * could tell that had happened.
 */
export function parseScope(text: string | null | undefined): ScopeRef | null {
  const raw = (text ?? '').trim()
  if (!raw) return null

  const at = raw.indexOf(SEP)
  const kindText = at === -1 ? raw : raw.slice(0, at)
  const id = at === -1 ? '' : raw.slice(at + 1).trim()

  if (!isScopeKind(kindText)) return null
  if (NO_ID.includes(kindText)) return at === -1 ? scope(kindText) : null
  if (!ID_PATTERN.test(id)) return null
  return scope(kindText, id)
}

export function isScopeKind(value: string): value is ScopeKind {
  return (SCOPE_KINDS as readonly string[]).includes(value)
}

export function scopesEqual(a: ScopeRef | null, b: ScopeRef | null): boolean {
  if (a === null || b === null) return a === b
  return a.kind === b.kind && a.id === b.id
}

/**
 * The next scope out, where the id alone decides it.
 *
 * `point:D03.XCBR1.PosSt` → `device:D03.XCBR1` → `bay:D03` → `station`.
 * A bay's voltage level is not derivable from its id, so it is not guessed
 * here — the backend answers that from the graph.
 */
export function parentScope(ref: ScopeRef): ScopeRef | null {
  if (ref.kind === 'station') return null
  if (ref.kind === 'point') {
    const cut = ref.id.lastIndexOf('.')
    return cut > 0 ? device(ref.id.slice(0, cut)) : STATION
  }
  if (ref.kind === 'device') {
    const cut = ref.id.indexOf('.')
    return cut > 0 ? bay(ref.id.slice(0, cut)) : STATION
  }
  return STATION
}

/** Whether `inner` lies inside `outer`, judged from ids alone. See scope.py. */
export function scopeContains(outer: ScopeRef, inner: ScopeRef): boolean {
  if (outer.kind === 'station') return true
  if (scopesEqual(outer, inner)) return true
  if (outer.kind === 'bay' && (inner.kind === 'device' || inner.kind === 'point')) {
    return inner.id.startsWith(`${outer.id}.`)
  }
  if (outer.kind === 'device' && inner.kind === 'point') {
    return inner.id.startsWith(`${outer.id}.`)
  }
  return false
}
