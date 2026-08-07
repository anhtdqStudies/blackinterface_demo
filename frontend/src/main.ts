import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { i18n } from './i18n'
import { router } from './router'
import { useSessionStore } from './stores/session'
import './styles.css'

/**
 * Identity first, then the router, then the screen.
 *
 * The order is the whole point and it is easy to get wrong: `app.use(router)`
 * *starts the first navigation immediately*, not at mount. Loading the session
 * alongside it means the entry guard runs before there is any answer to "who is
 * this" — and an unauthenticated browser then lands on the station diagram
 * instead of the login form. That is exactly what happened the first time this
 * was written.
 *
 * So `/api/me` is awaited before the router is installed at all. `isReady()`
 * then lets the first navigation — including any redirect to the login screen —
 * settle before anything is painted, so nobody sees the wrong page flash past.
 *
 * A failed load does not stop the app. The session is then empty, the guard
 * sends the browser to the login screen, and the failure is visible there —
 * better than a blank page that explains nothing.
 */
async function start(): Promise<void> {
  const pinia = createPinia()
  const app = createApp(App).use(pinia).use(i18n)

  await useSessionStore(pinia).load()

  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void start()
