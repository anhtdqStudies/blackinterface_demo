import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import type { Capability, Role } from '@/authz'
import { bay as bayScope, formatScope, parseScope, STATION } from '@/scope'
import { useSessionStore } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    /** The capability this screen needs. Absent = any signed-in caller. */
    requires?: Capability
    /** Reachable without signing in. Only the login screen. */
    public?: boolean
  }
}

/**
 * Hash history on purpose: FastAPI serves `dist/index.html` at `/` only, and
 * hash routing means a refresh on a deep link works without a catch-all route
 * on the server. One fewer thing to get wrong in the installer (ADR-0009).
 *
 * `/ops/:scope?l=<preset>` is the shape that matters (ADR-0010, ADR-0014). The
 * scope ref in the path is the *same string* used as a pane key, as an agent
 * tool argument and as an evidence subject — so a screen can be linked to,
 * reloaded into, and later handed to the agent as "what I am looking at".
 *
 * Subject in the path, arrangement in the query, and the two are treated
 * differently on purpose: an unparseable scope is redirected (below), an
 * unknown preset is quietly replaced by the default (`layoutFor`). Only the
 * first can make the address bar and the screen disagree about the station.
 *
 * Legacy paths redirect rather than 404: bookmarks from before GĐ 1.5 should
 * land somewhere sensible.
 */
const OPS = '/ops'
const HOME = `${OPS}/${formatScope(STATION)}`
export const ENG_PATH = '/eng'

export const LOGIN_PATH = '/login'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: HOME },
  {
    path: LOGIN_PATH,
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: `${OPS}/:scope`,
    name: 'ops',
    component: () => import('@/views/WorkspaceView.vue'),
  },
  {
    path: ENG_PATH,
    name: 'eng',
    component: () => import('@/views/EngView.vue'),
    meta: { requires: 'model.connect' },
  },
  {
    path: '/bay/:bayId',
    redirect: (to) => ({
      name: 'ops',
      params: { scope: formatScope(bayScope(String(to.params.bayId))) },
      query: { l: 'monitor' },
    }),
  },
  {
    path: '/issues',
    redirect: () => ({
      name: 'ops',
      params: { scope: formatScope(STATION) },
      query: { l: 'monitor' },
    }),
  },
  { path: '/projects', redirect: ENG_PATH },
  { path: '/station', redirect: HOME },
  { path: '/:pathMatch(.*)*', redirect: HOME },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

/**
 * A scope that does not parse is sent back to the station.
 *
 * Deliberately a redirect and not a silent fallback: the address bar and the
 * screen must agree. Quietly answering "the whole station" for a URL that asked
 * about one bay is the failure mode this guard exists to prevent.
 */
router.beforeEach((to) => {
  if (to.name !== 'ops') return true
  const raw = to.params.scope
  if (typeof raw === 'string' && parseScope(raw)) return true
  // The query survives the correction: a bad scope is no reason to also throw
  // away the layout the link was carrying.
  return { name: 'ops', params: { scope: formatScope(STATION) }, query: to.query }
})

/**
 * Signed in, and allowed to be here (ADR-0016 §4, ADR-0017).
 *
 * Both halves are tidiness, not security: every facet behind every screen
 * checks the same things itself, and those checks are the ones that decide.
 * What this guard buys is a person seeing a login form instead of a page of
 * 401s, and a landing screen instead of a page of 403s.
 *
 * The redirect carries where they were going, so a deep link survives the
 * detour through the login form — the bookmark an operator actually uses.
 *
 * Note there is **no "session not loaded yet" exemption**. An earlier version
 * had one, and it was not a nicety: `app.use(router)` starts the first
 * navigation before an awaited load can finish, so the exemption fired on
 * exactly the navigation that mattered and let an anonymous browser through to
 * the station. `main.ts` now loads the session before installing the router,
 * and this guard treats "we do not know" the same as "not signed in".
 */
router.beforeEach((to) => {
  if (to.meta.public) return true
  const session = useSessionStore()

  if (!session.authenticated) {
    return { path: LOGIN_PATH, query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  }
  const needed = to.meta.requires
  if (!needed || session.can(needed)) return true
  return landingFor(session.roles)
})

/**
 * Where a set of roles lands (ADR-0016 §8, GĐ 1.5 lô 3).
 *
 * Engineers land on `#/eng` — model work, not the SLD. Everyone else lands on
 * the operator workspace at `#/ops/station`.
 */
export function landingFor(roles: readonly Role[]): string {
  if (roles.length === 1 && roles[0] === 'engineer') return ENG_PATH
  return HOME
}

/** The workspace, aimed at a scope. Views never build these paths themselves. */
export function opsPath(ref: Parameters<typeof formatScope>[0]): string {
  return `${OPS}/${formatScope(ref)}`
}

export { bayScope }
export const HOME_PATH = HOME
