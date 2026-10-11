<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { useNotificacaoStore } from '@/stores/notificacao'
import { useOfflineStore } from '@/stores/offline'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'
import { formatarDataHora } from '@/utils/formato'

const session = useSessionStore()
const ui = useUiStore()
const offline = useOfflineStore()
const notificacao = useNotificacaoStore()

const nomeUsuario = computed(() => session.usuario?.nome ?? 'Visitante')
const ultimaSync = computed(() =>
  offline.ultimaSincronizacao ? formatarDataHora(offline.ultimaSincronizacao) : 'nunca',
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

onUnmounted(() => notificacao.desconectar())
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
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
        <RouterLink :to="{ name: 'mapa' }" class="text-lg font-semibold text-primary">
          Ygapé
        </RouterLink>

        <nav aria-label="Navegação principal" class="flex flex-1 flex-wrap items-center gap-1">
          <RouterLink
            :to="{ name: 'mapa' }"
            class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
            active-class="bg-surface-muted font-medium"
          >
            Mapa
          </RouterLink>
          <RouterLink
            :to="{ name: 'rota-nova' }"
            class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
            active-class="bg-surface-muted font-medium"
          >
            Nova rota
          </RouterLink>
          <RouterLink
            :to="{ name: 'historico' }"
            class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
            active-class="bg-surface-muted font-medium"
          >
            Histórico
          </RouterLink>
          <RouterLink
            :to="{ name: 'configuracoes' }"
            class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
            active-class="bg-surface-muted font-medium"
          >
            Configurações
          </RouterLink>

          <template v-if="session.ehAdmin">
            <span class="mx-1 hidden h-4 w-px bg-edge sm:inline-block" aria-hidden="true" />
            <RouterLink
              :to="{ name: 'admin-usuarios' }"
              class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
              active-class="bg-surface-muted font-medium"
            >
              Usuários
            </RouterLink>
            <RouterLink
              :to="{ name: 'admin-coleta' }"
              class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
              active-class="bg-surface-muted font-medium"
            >
              Coleta
            </RouterLink>
            <RouterLink
              :to="{ name: 'admin-logs' }"
              class="rounded px-3 py-2 text-sm hover:bg-surface-muted"
              active-class="bg-surface-muted font-medium"
            >
              Logs
            </RouterLink>
          </template>
        </nav>

        <div class="flex items-center gap-2">
          <span
            class="rounded-full px-2 py-1 text-xs font-medium"
            :class="offline.online ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'"
            aria-live="polite"
          >
            {{ offline.online ? 'Online' : 'Offline' }}
          </span>

          <button
            type="button"
            class="rounded border border-edge px-2 py-1 text-xs hover:bg-surface-muted disabled:opacity-60"
            :disabled="offline.sincronizando || !offline.online"
            :title="`Última sincronização: ${ultimaSync}`"
            @click="offline.sincronizar()"
          >
            {{ offline.sincronizando ? 'Sincronizando…' : 'Sincronizar' }}
            <span v-if="offline.pendentes > 0">· {{ offline.pendentes }}</span>
          </button>

          <button
            type="button"
            class="rounded border border-edge px-2 py-1 text-xs hover:bg-surface-muted"
            :aria-pressed="ui.tema === 'escuro'"
            @click="ui.alternarTema()"
          >
            {{ ui.tema === 'claro' ? 'Tema escuro' : 'Tema claro' }}
          </button>

          <template v-if="session.autenticado">
            <span class="hidden text-sm text-ink-muted sm:inline">{{ nomeUsuario }}</span>
            <button
              type="button"
              class="rounded border border-edge px-2 py-1 text-xs hover:bg-surface-muted"
              @click="session.logout()"
            >
              Sair
            </button>
          </template>
          <RouterLink
            v-else
            :to="{ name: 'login' }"
            class="rounded bg-primary px-3 py-1 text-xs font-medium text-white hover:bg-primary-strong"
          >
            Entrar
          </RouterLink>
        </div>
      </div>

      <p
        v-if="!offline.online"
        class="bg-warning/10 px-4 py-1 text-center text-xs text-warning"
        role="status"
      >
        Sem conexão — usando dados locais (última sincronização: {{ ultimaSync }}).
      </p>
    </header>

    <main id="conteudo" class="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
      <RouterView />
    </main>

    <footer class="border-t border-edge px-4 py-4 text-center text-xs text-ink-muted">
      Ygapé — ferramenta de apoio ao planejamento. Não substitui cartas e procedimentos oficiais.
    </footer>

    <div
      v-if="notificacao.avisos.length"
      class="fixed bottom-4 right-4 z-40 w-80 max-w-[90vw] space-y-2"
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
