/**
 * Capabilities — the frontend half of `backend/src/blackinterface/domain/authz.py`.
 *
 * Duplicated for the same reason `scope.ts` is: the list has to exist in both
 * languages, so `tools/check.py` compares them mechanically rather than
 * trusting anyone to remember. Adding a capability on one side and not the
 * other fails the repo check.
 *
 * **Nothing here is a security boundary.** The frontend hides what the caller
 * cannot use so the screen stays legible; the enforcement is `requires()` on
 * each facet, and it runs whether or not anything was hidden (ADR-0016 §4).
 * If a button is visible that should not be, the API still says no.
 */

export const CAPABILITIES = [
  'station.read',
  'alarm.read',
  'alarm.ack',
  'event.read',
  'trend.read',
  'report.read',
  'report.export',
  'knowledge.read',
  'knowledge.write',
  'protection.read',
  'agent.ask',
  // Choosing the language model and holding its key. Not one of the `model.*`
  // three below — those mean the *station* model.
  'assistant.config',
  'control.draft',
  'control.sign',
  'model.connect',
  'model.edit',
  'model.publish',
  'binding.read',
  'audit.read',
  'account.manage',
] as const

export type Capability = (typeof CAPABILITIES)[number]

export const ROLES = [
  'operator',
  'supervisor',
  'maintenance',
  'protection',
  'admin',
  'engineer',
] as const

export type Role = (typeof ROLES)[number]

export function isCapability(value: string): value is Capability {
  return (CAPABILITIES as readonly string[]).includes(value)
}

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value)
}
