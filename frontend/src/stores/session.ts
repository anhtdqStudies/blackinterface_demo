/**
 * Who is using this screen, and what they may therefore see (ADR-0016, ADR-0017).
 *
 * The session itself is an HttpOnly cookie the browser carries on its own, so
 * nothing here holds a credential. This store holds the *answer* to "who am I",
 * refreshed from `/api/me`.
 *
 * Components ask `can('model.connect')`, never `roles.includes('engineer')`.
 * Asking by role means every component that named the old roles has to be
 * edited when a role is added, which is exactly the retrofit ADR-0016 §4 is
 * trying to avoid.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError, api, type Me } from '@/api/client'
import { isCapability, isRole, type Capability, type Role } from '@/authz'

export const useSessionStore = defineStore('session', () => {
  const user = ref('')
  const displayName = ref('')
  const roles = ref<Role[]>([])
  const capabilities = ref<Set<Capability>>(new Set())
  const authenticated = ref(false)
  /** `env` means identity comes from `BI_ROLE`; there is nothing to sign out of. */
  const authMode = ref<'session' | 'env'>('session')
  const loaded = ref(false)
  const error = ref<string | null>(null)

  /**
   * A capability the backend knows and this build does not is dropped, not
   * treated as granted. Failing closed on an unknown name keeps a newer server
   * from silently unlocking a screen an older frontend cannot render properly.
   */
  function apply(me: Me): void {
    user.value = me.user
    displayName.value = me.display_name || me.user
    roles.value = me.roles.filter(isRole)
    capabilities.value = new Set(me.capabilities.filter(isCapability))
    authenticated.value = me.authenticated
    authMode.value = me.auth_mode === 'env' ? 'env' : 'session'
  }

  function clear(): void {
    user.value = ''
    displayName.value = ''
    roles.value = []
    capabilities.value = new Set()
    authenticated.value = false
  }

  async function load(): Promise<void> {
    try {
      apply(await api.me())
      error.value = null
    } catch (cause) {
      // Unreachable or broken means no identity — never fall back to "allow".
      clear()
      error.value = cause instanceof ApiError ? cause.message : String(cause)
    } finally {
      loaded.value = true
    }
  }

  /** Throws on a refused sign-in, so the login screen can show why. */
  async function signIn(username: string, password: string): Promise<void> {
    apply(await api.login(username, password))
    error.value = null
  }

  async function signOut(): Promise<void> {
    try {
      apply(await api.logout())
    } finally {
      // Whatever the server said, this browser is done. A failed logout that
      // left the screen looking signed in would be worse than a noisy one.
      clear()
    }
  }

  function can(capability: Capability): boolean {
    return capabilities.value.has(capability)
  }

  return {
    user,
    displayName,
    roles,
    capabilities,
    authenticated,
    authMode,
    loaded,
    error,
    load,
    signIn,
    signOut,
    can,
  }
})
