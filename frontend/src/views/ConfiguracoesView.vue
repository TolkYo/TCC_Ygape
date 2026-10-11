<script setup lang="ts">
import { reactive, ref } from 'vue'

import BaseButton from '@/components/ui/BaseButton.vue'
import { ApiProblem } from '@/services/http'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const session = useSessionStore()

const perfil = reactive({ nome: session.usuario?.nome ?? '', senha: '' })
const salvando = ref(false)
const erro = ref<string | null>(null)
const aviso = ref<string | null>(null)

async function salvarPerfil(): Promise<void> {
  salvando.value = true
  erro.value = null
  aviso.value = null
  try {
    await session.atualizarPerfil({
      nome: perfil.nome || undefined,
      senha: perfil.senha || undefined,
    })
    perfil.senha = ''
    aviso.value = 'Perfil atualizado com sucesso.'
  } catch (e) {
    erro.value = e instanceof ApiProblem ? e.message : 'Falha ao atualizar o perfil.'
  } finally {
    salvando.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Configurações</h1>
      <p class="text-sm text-ink-muted">Preferências de acessibilidade e aparência.</p>
    </header>

    <section class="max-w-lg space-y-4 rounded-lg border border-edge bg-surface-elevated p-4">
      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium">Tema</p>
          <p class="text-xs text-ink-muted">Claro ou escuro. Atual: {{ ui.tema }}.</p>
        </div>
        <BaseButton variante="secundaria" @click="ui.alternarTema()">Alternar</BaseButton>
      </div>

      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium">Alto contraste</p>
          <p class="text-xs text-ink-muted">
            Reforça contraste de texto e bordas. Atual:
            {{ ui.altoContraste ? 'ligado' : 'desligado' }}.
          </p>
        </div>
        <BaseButton variante="secundaria" @click="ui.alternarContraste()">Alternar</BaseButton>
      </div>

      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium">Tamanho do texto</p>
          <p class="text-xs text-ink-muted">Escala atual: nível {{ ui.escalaFonte + 1 }} de 3.</p>
        </div>
        <BaseButton variante="secundaria" @click="ui.ciclarFonte()">Aumentar</BaseButton>
      </div>
    </section>

    <section v-if="session.autenticado" class="max-w-lg space-y-4">
      <div>
        <h2 class="text-lg font-semibold">Perfil</h2>
        <p class="text-sm text-ink-muted">Atualize seu nome ou senha de acesso.</p>
      </div>

      <form
        class="space-y-4 rounded-lg border border-edge bg-surface-elevated p-4"
        @submit.prevent="salvarPerfil"
      >
        <div>
          <label for="perfil-nome" class="mb-1 block text-sm font-medium">Nome</label>
          <input
            id="perfil-nome"
            v-model="perfil.nome"
            minlength="2"
            class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
          />
        </div>
        <div>
          <label for="perfil-senha" class="mb-1 block text-sm font-medium">
            Nova senha (opcional)
          </label>
          <input
            id="perfil-senha"
            v-model="perfil.senha"
            type="password"
            minlength="8"
            class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
          />
        </div>

        <p v-if="erro" role="alert" class="text-sm text-danger">{{ erro }}</p>
        <p v-if="aviso" role="status" class="text-sm text-success">{{ aviso }}</p>

        <BaseButton tipo="submit" :desabilitado="salvando">
          {{ salvando ? 'Salvando…' : 'Salvar perfil' }}
        </BaseButton>
      </form>
    </section>
  </div>
</template>
