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
  <div class="grid min-h-screen place-items-center bg-surface p-4">
    <section
      class="w-full max-w-sm rounded-lg border border-edge bg-surface-elevated p-6 shadow-sm"
    >
      <h1 class="mb-1 text-xl font-semibold">Entrar no Ygapé</h1>
      <p class="mb-4 text-sm text-ink-muted">Acesso para pilotos e administradores.</p>

      <form class="space-y-4" novalidate @submit.prevent="entrar">
        <div>
          <label for="email" class="mb-1 block text-sm font-medium">E-mail</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="username"
            required
            class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
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
            class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
          />
        </div>

        <p v-if="erro" role="alert" class="rounded bg-danger/10 px-3 py-2 text-sm text-danger">
          {{ erro }}
        </p>

        <BaseButton tipo="submit" :desabilitado="session.carregando" class="w-full">
          {{ session.carregando ? 'Entrando…' : 'Entrar' }}
        </BaseButton>
      </form>
    </section>
  </div>
</template>
