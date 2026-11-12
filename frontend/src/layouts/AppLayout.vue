<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { useNotificacaoStore } from '@/stores/notificacao'
import { useOfflineStore } from '@/stores/offline'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'
import { formatarDataHora } from '@/utils/formato'

const route = useRoute()
const session = useSessionStore()
const ui = useUiStore()
const offline = useOfflineStore()
const notificacao = useNotificacaoStore()

const menuAberto = ref(false)

const links = [
  { name: 'mapa', label: 'Mapa' },
  { name: 'rota-nova', label: 'Nova rota' },
  { name: 'historico', label: 'Histórico' },
  { name: 'configuracoes', label: 'Configurações' },
] as const

const linksAdmin = [
  { name: 'admin-usuarios', label: 'Usuários' },
  { name: 'admin-coleta', label: 'Coleta' },
  { name: 'admin-logs', label: 'Logs' },
] as const

const nomeUsuario = computed(() => session.usuario?.nome ?? 'Visitante')
const ultimaSync = computed(() =>
  offline.ultimaSincronizacao ? formatarDataHora(offline.ultimaSincronizacao) : 'nunca',
)
const rotuloTema = computed(() =>
  ui.tema === 'claro' ? 'Ativar tema escuro' : 'Ativar tema claro',
)

watch(
  () => route.fullPath,
  () => {
    menuAberto.value = false
  },
)

watch(
  () => session.autenticado,
  (autenticado) => {
    if (autenticado) {
      notificacao.conectar()
    } else {
      notificacao.desconectar()
    }
  },
  { immediate: true },
)

// @id FUN-TS-UI-037 | @categoria UI | @catalogo FUNCOES.md
function fecharMenuComEsc(evento: KeyboardEvent): void {
  if (evento.key === 'Escape') {
    menuAberto.value = false
  }
}

// @id FUN-TS-UI-038 | @categoria UI | @catalogo FUNCOES.md
function sair(): void {
  menuAberto.value = false
  session.logout()
}

onMounted(() => window.addEventListener('keydown', fecharMenuComEsc))
onUnmounted(() => {
  window.removeEventListener('keydown', fecharMenuComEsc)
  notificacao.desconectar()
})
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface text-ink">
    <a
      href="#conteudo"
      class="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-white"
    >
      Pular para o conteúdo
    </a>

    <header class="border-b border-edge bg-surface-elevated">
      <div class="brand-rule h-0.5 w-full" aria-hidden="true" />
      <div class="mx-auto flex max-w-7xl items-center gap-2 px-3 py-2 sm:px-4 md:gap-3 md:py-3">
        <RouterLink
          :to="{ name: 'mapa' }"
          class="flex shrink-0 items-center"
          aria-label="Ygapé — página inicial"
        >
          <img
            src="/brand/logo-horizontal-claro.png"
            alt="Ygapé — Sistema Inteligente de Roteamento Fluvial"
            class="h-9 w-[6.75rem] dark:hidden sm:h-10 sm:w-[7.5rem]"
          />
          <img
            src="/brand/logo-horizontal-escuro.png"
            alt=""
            aria-hidden="true"
            class="hidden h-9 w-[6.75rem] dark:block sm:h-10 sm:w-[7.5rem]"
          />
        </RouterLink>

        <nav
          aria-label="Navegação principal"
          class="ml-2 hidden min-w-0 flex-1 items-center gap-1 lg:flex"
        >
          <RouterLink
            v-for="link in links"
            :key="link.name"
            :to="{ name: link.name }"
            class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
            active-class="bg-surface-muted font-medium"
          >
            {{ link.label }}
          </RouterLink>

          <template v-if="session.ehAdmin">
            <span class="mx-1 h-4 w-px bg-edge" aria-hidden="true" />
            <RouterLink
              v-for="link in linksAdmin"
              :key="link.name"
              :to="{ name: link.name }"
              class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
              active-class="bg-surface-muted font-medium"
            >
              {{ link.label }}
            </RouterLink>
          </template>
        </nav>

        <div class="ml-auto flex items-center gap-1.5 sm:gap-2">
          <span
            class="rounded-full px-2 py-1 text-xs font-medium"
            :class="offline.online ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'"
            aria-live="polite"
          >
            {{ offline.online ? 'Online' : 'Offline' }}
          </span>

          <button
            type="button"
            class="hidden min-h-9 items-center rounded border border-edge px-2 py-1 text-xs hover:bg-surface-muted disabled:opacity-60 sm:inline-flex"
            :disabled="offline.sincronizando || !offline.online"
            :title="`Última sincronização: ${ultimaSync}`"
            @click="offline.sincronizar()"
          >
            {{ offline.sincronizando ? 'Sincronizando…' : 'Sincronizar' }}
            <span v-if="offline.pendentes > 0">· {{ offline.pendentes }}</span>
          </button>

          <button
            type="button"
            class="inline-flex min-h-11 min-w-11 items-center justify-center rounded border border-edge px-2 py-1 text-xs hover:bg-surface-muted"
            :aria-label="rotuloTema"
            :title="rotuloTema"
            @click="ui.alternarTema()"
          >
            <svg
              v-if="ui.tema === 'claro'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="4" />
              <path
                d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
              />
            </svg>
          </button>

          <template v-if="session.autenticado">
            <span class="hidden text-sm text-ink-muted xl:inline">{{ nomeUsuario }}</span>
            <button
              type="button"
              class="hidden min-h-9 items-center rounded border border-edge px-2 py-1 text-xs hover:bg-surface-muted lg:inline-flex"
              @click="sair"
            >
              Sair
            </button>
          </template>
          <RouterLink
            v-else
            :to="{ name: 'login' }"
            class="hidden min-h-9 items-center rounded bg-primary px-3 py-1 text-xs font-medium text-white hover:bg-primary-strong lg:inline-flex"
          >
            Entrar
          </RouterLink>

          <button
            type="button"
            class="inline-flex min-h-11 min-w-11 items-center justify-center rounded border border-edge px-2 py-1 hover:bg-surface-muted lg:hidden"
            :aria-expanded="menuAberto"
            aria-controls="menu-mobile"
            :aria-label="menuAberto ? 'Fechar menu' : 'Abrir menu'"
            @click="menuAberto = !menuAberto"
          >
            <svg
              v-if="!menuAberto"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              class="h-5 w-5"
              aria-hidden="true"
            >
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              class="h-5 w-5"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
      </div>

      <div
        v-if="menuAberto"
        id="menu-mobile"
        class="max-h-[calc(100vh-4rem)] overflow-y-auto border-t border-edge lg:hidden"
      >
        <nav aria-label="Navegação principal (menu)" class="mx-auto max-w-7xl px-2 py-2">
          <p v-if="session.autenticado" class="px-3 py-2 text-xs text-ink-muted">
            Conectado como <span class="font-medium text-ink">{{ nomeUsuario }}</span>
          </p>

          <RouterLink
            v-for="link in links"
            :key="link.name"
            :to="{ name: link.name }"
            class="flex min-h-11 items-center rounded px-3 text-sm hover:bg-surface-muted"
            active-class="bg-surface-muted font-medium text-primary"
          >
            {{ link.label }}
          </RouterLink>

          <template v-if="session.ehAdmin">
            <p
              class="mt-2 border-t border-edge px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-ink-muted"
            >
              Administração
            </p>
            <RouterLink
              v-for="link in linksAdmin"
              :key="link.name"
              :to="{ name: link.name }"
              class="flex min-h-11 items-center rounded px-3 text-sm hover:bg-surface-muted"
              active-class="bg-surface-muted font-medium text-primary"
            >
              {{ link.label }}
            </RouterLink>
          </template>

          <div class="mt-2 flex flex-wrap items-center gap-2 border-t border-edge px-3 pb-1 pt-3">
            <button
              type="button"
              class="inline-flex min-h-11 items-center rounded border border-edge px-3 text-sm hover:bg-surface-muted disabled:opacity-60"
              :disabled="offline.sincronizando || !offline.online"
              @click="offline.sincronizar()"
            >
              {{ offline.sincronizando ? 'Sincronizando…' : 'Sincronizar' }}
              <span v-if="offline.pendentes > 0">· {{ offline.pendentes }}</span>
            </button>
            <button
              v-if="session.autenticado"
              type="button"
              class="inline-flex min-h-11 items-center rounded border border-edge px-3 text-sm hover:bg-surface-muted"
              @click="sair"
            >
              Sair
            </button>
            <RouterLink
              v-else
              :to="{ name: 'login' }"
              class="inline-flex min-h-11 items-center rounded bg-primary px-3 text-sm font-medium text-white hover:bg-primary-strong"
            >
              Entrar
            </RouterLink>
          </div>

          <p class="px-3 pb-2 pt-2 text-xs text-ink-muted">
            Última sincronização: {{ ultimaSync }}
          </p>
        </nav>
      </div>

      <p
        v-if="!offline.online"
        class="bg-warning/10 px-4 py-1 text-center text-xs text-warning"
        role="status"
      >
        Sem conexão — usando dados locais (última sincronização: {{ ultimaSync }}).
      </p>
    </header>

    <main class="mx-auto w-full max-w-7xl flex-1 overflow-x-clip px-3 py-4 sm:px-4 sm:py-6">
      <RouterView />
    </main>

    <footer class="border-t border-edge px-4 py-4">
      <div class="mx-auto flex max-w-7xl flex-col items-center gap-1 text-center text-xs text-ink-muted">
        <div class="flex items-center gap-2">
          <img src="/brand/icone.png" alt="" aria-hidden="true" class="h-5 w-5" />
          <span class="font-display text-[0.7rem] font-medium uppercase tracking-[0.18em] text-ink">
            Sistema Inteligente de Roteamento Fluvial
          </span>
        </div>
        <p>Ygapé — ferramenta de apoio ao planejamento. Não substitui cartas e procedimentos oficiais.</p>
      </div>
    </footer>

    <div
      v-if="notificacao.avisos.length"
      class="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-3 z-40 w-80 max-w-[calc(100vw-1.5rem)] space-y-2 sm:right-4"
      aria-live="polite"
    >
      <div
        v-for="aviso in notificacao.avisos"
        :key="aviso.id"
        class="rounded-lg border border-warning/40 bg-surface-elevated p-3 text-sm shadow-lg"
      >
        <p class="text-ink">{{ aviso.texto }}</p>
        <button
          type="button"
          class="mt-2 text-xs font-medium text-primary underline"
          @click="notificacao.limparAviso(aviso.id)"
        >
          Fechar
        </button>
      </div>
    </div>
  </div>
</template>
