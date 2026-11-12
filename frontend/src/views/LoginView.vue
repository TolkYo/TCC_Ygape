<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BaseButton from '@/components/ui/BaseButton.vue'
import { ApiProblem } from '@/services/http'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const senha = ref('')
const erro = ref<string | null>(null)

// @id FUN-TS-UI-015 | @categoria UI | @catalogo FUNCOES.md
async function entrar(): Promise<void> {
  erro.value = null
  try {
    await session.login(email.value.trim(), senha.value)
    const destino = typeof route.query.redirect === 'string' ? route.query.redirect : '/mapa'
    await router.push(destino)
  } catch (e) {
    erro.value =
      e instanceof ApiProblem ? e.message : 'Não foi possível entrar. Verifique a conexão.'
  }
}
</script>

<template>
  <div class="grid min-h-screen place-items-center bg-surface p-4 sm:p-6">
    <div
      class="w-full min-w-0 max-w-4xl overflow-hidden rounded-2xl border border-edge bg-surface-elevated shadow-xl md:grid md:grid-cols-2"
    >
      <aside
        class="brand-panel relative hidden flex-col justify-between overflow-hidden p-8 text-brand-praia md:flex"
      >
        <div
          class="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full border border-white/15"
          aria-hidden="true"
        />
        <div
          class="pointer-events-none absolute -bottom-24 -left-20 h-64 w-64 rounded-full border border-white/10"
          aria-hidden="true"
        />

        <div class="relative">
          <img
            src="/brand/logo-horizontal-escuro.png"
            alt="Ygapé — Sistema Inteligente de Roteamento Fluvial"
            class="h-10 w-[7.5rem]"
          />
          <p class="mt-6 max-w-xs text-sm leading-relaxed text-brand-praia/80">
            Rotas mais rápidas e seguras nos rios do Amazonas, considerando o nível do rio, o
            calado da embarcação e a correnteza.
          </p>
        </div>

        <ul class="relative mt-10 space-y-3 text-sm text-brand-praia/90">
          <li class="flex items-start gap-3">
            <span
              class="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15"
              aria-hidden="true"
            >
              <svg viewBox="0 0 20 20" fill="none" class="h-3 w-3">
                <path
                  d="M4 10.5l4 4 8-9"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
            Nível do rio e previsão em tempo real
          </li>
          <li class="flex items-start gap-3">
            <span
              class="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15"
              aria-hidden="true"
            >
              <svg viewBox="0 0 20 20" fill="none" class="h-3 w-3">
                <path
                  d="M4 10.5l4 4 8-9"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
            Planejamento de rotas por calado e correnteza
          </li>
          <li class="flex items-start gap-3">
            <span
              class="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15"
              aria-hidden="true"
            >
              <svg viewBox="0 0 20 20" fill="none" class="h-3 w-3">
                <path
                  d="M4 10.5l4 4 8-9"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </span>
            Funcionamento offline com sincronização
          </li>
        </ul>

        <p
          class="brand-rule relative mt-10 h-0.5 w-16 rounded-full"
          aria-hidden="true"
        />
      </aside>

      <section class="min-w-0 p-6 sm:p-8">
        <div class="mb-6 md:hidden">
          <img
            src="/brand/logo-horizontal-claro.png"
            alt="Ygapé — Sistema Inteligente de Roteamento Fluvial"
            class="h-9 w-[6.75rem] dark:hidden"
          />
          <img
            src="/brand/logo-horizontal-escuro.png"
            alt="Ygapé — Sistema Inteligente de Roteamento Fluvial"
            class="hidden h-9 w-[6.75rem] dark:block"
          />
        </div>

        <p class="font-display text-[0.65rem] font-medium uppercase tracking-[0.24em] text-info">
          Acesso restrito
        </p>
        <h1 class="mt-1 text-2xl font-semibold tracking-tight">Entrar no Ygapé</h1>
        <p class="mb-6 mt-1 text-sm text-ink-muted">Acesso para capitães e administradores.</p>

        <form class="space-y-4" novalidate @submit.prevent="entrar">
          <div>
            <label for="email" class="mb-1 block text-sm font-medium">E-mail</label>
            <input
              id="email"
              v-model="email"
              type="email"
              autocomplete="username"
              required
              class="w-full rounded-lg border border-edge bg-surface px-3 py-2.5 text-sm focus:outline focus:outline-2 focus:outline-primary"
            />
          </div>

          <div>
            <label for="senha" class="mb-1 block text-sm font-medium">Senha</label>
            <input
              id="senha"
              v-model="senha"
              type="password"
              autocomplete="current-password"
              required
              class="w-full rounded-lg border border-edge bg-surface px-3 py-2.5 text-sm focus:outline focus:outline-2 focus:outline-primary"
            />
          </div>

          <p v-if="erro" role="alert" class="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">
            {{ erro }}
          </p>

          <BaseButton tipo="submit" :desabilitado="session.carregando" class="w-full">
            {{ session.carregando ? 'Entrando…' : 'Entrar' }}
          </BaseButton>
        </form>

        <p class="mt-6 border-t border-edge pt-4 text-xs text-ink-muted">
          Sistema Inteligente de Roteamento Fluvial · Ygapé
        </p>
      </section>
    </div>
  </div>
</template>
