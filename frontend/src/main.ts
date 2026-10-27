import './styles/fonts.css'
import './styles/tokens.css'
import './styles/base.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/client'
import { useAuthStore } from './stores/auth'

const app = createApp(App)

app.use(createPinia())
app.use(router)

const auth = useAuthStore()
// An account-only endpoint said the session has gone: forget the user and ask them to log in.
setUnauthorizedHandler(() => {
  auth.sessionExpired()
  const next = router.currentRoute.value.fullPath
  if (!next.startsWith('/login')) router.push({ path: '/login', query: { next } })
})

app.mount('#app')
// Who is this? (account / guest / visitor). Also sets the CSRF cookie. Play never waits on it.
auth.load().catch(() => {})
