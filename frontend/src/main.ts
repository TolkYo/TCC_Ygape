import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './app/router'
import { useOfflineStore } from './stores/offline'
import { useSessionStore } from './stores/session'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const session = useSessionStore(pinia)

// Restaura a sessão (token em localStorage) antes de instalar o router, para que
// a navegação inicial já encontre o usuário autenticado nos guards de rota.
session.restaurar().finally(() => {
  app.use(router)
  app.mount('#app')

  const offline = useOfflineStore(pinia)
  offline.registarListeners()
  void offline.atualizarContadores()
  if (offline.online) {
    void offline.sincronizar()
  }
})

// O Service Worker (cache de assets + API) só é registrado no build de produção.
if ('serviceWorker' in navigator && (import.meta.env.PROD || window.isSecureContext)) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => undefined)
  })
}
