<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import BaseButton from '@/components/ui/BaseButton.vue'
import { api } from '@/services/endpoints'
import { ApiProblem } from '@/services/http'
import { useEstacoesStore } from '@/stores/estacoes'

const estacoes = useEstacoesStore()

const filtro = reactive<{ estacoes: string[]; periodo_inicio: string; periodo_fim: string }>({
  estacoes: [],
  periodo_inicio: '',
  periodo_fim: '',
})

const enviando = ref(false)
const erro = ref<string | null>(null)
const resultado = ref<string | null>(null)

onMounted(() => {
  estacoes.carregar()
})

async function solicitar(): Promise<void> {
  enviando.value = true
  erro.value = null
  resultado.value = null
  try {
    const resposta = await api.coletarNiveis({
      estacoes: filtro.estacoes,
      periodo_inicio: filtro.periodo_inicio || null,
      periodo_fim: filtro.periodo_fim || null,
    })
    resultado.value = `Coleta solicitada: ${JSON.stringify(resposta)}`
  } catch (e) {
    erro.value =
      e instanceof ApiProblem
        ? e.message
        : 'Não foi possível solicitar a coleta. Verifique a conexão com a API.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Coleta de níveis (ANA)</h1>
      <p class="text-sm text-ink-muted">
        Solicita a coleta de telemetria para as estações selecionadas.
      </p>
    </header>

    <section
      class="rounded-lg border border-dashed border-ink-muted/40 bg-surface-muted/40 p-4 text-sm text-ink-muted"
    >
      A coleta em produção roda pelo serviço agendado (coletores ANA SOAP/REST). O endpoint
      administrativo ainda não enfileira tarefas e responde <code>501</code> — use esta tela para
      registrar a intenção e acompanhar a evolução.
    </section>

    <form
      class="grid gap-4 rounded-lg border border-edge bg-surface-elevated p-4 sm:grid-cols-2"
      @submit.prevent="solicitar"
    >
      <div>
        <label for="periodo_inicio" class="mb-1 block text-sm font-medium">Período — início</label>
        <input
          id="periodo_inicio"
          v-model="filtro.periodo_inicio"
          type="date"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>
      <div>
        <label for="periodo_fim" class="mb-1 block text-sm font-medium">Período — fim</label>
        <input
          id="periodo_fim"
          v-model="filtro.periodo_fim"
          type="date"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>

      <div class="sm:col-span-2">
        <label for="estacoes" class="mb-1 block text-sm font-medium">
          Estações (deixe vazio para todas do trecho)
        </label>
        <select
          id="estacoes"
          v-model="filtro.estacoes"
          multiple
          size="6"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        >
          <option
            v-for="estacao in estacoes.itens"
            :key="estacao.codigo_estacao"
            :value="estacao.codigo_estacao"
          >
            {{ estacao.nome_estacao }} ({{ estacao.codigo_estacao }})
          </option>
        </select>
      </div>

      <div class="sm:col-span-2">
        <BaseButton tipo="submit" :desabilitado="enviando">
          {{ enviando ? 'Solicitando…' : 'Solicitar coleta' }}
        </BaseButton>
      </div>
    </form>

    <p v-if="erro" role="alert" class="rounded bg-warning/10 px-3 py-2 text-sm text-warning">
      {{ erro }}
    </p>
    <p v-if="resultado" role="status" class="rounded bg-success/10 px-3 py-2 text-sm text-success">
      {{ resultado }}
    </p>
  </div>
</template>
