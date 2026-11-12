<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { api } from '@/services/endpoints'
import { ApiProblem } from '@/services/http'
import { useEstacoesStore } from '@/stores/estacoes'
import type { ColetaJob } from '@/types/api'

const estacoes = useEstacoesStore()

const filtro = reactive<{ estacoes: string[]; periodo_inicio: string; periodo_fim: string }>({
  estacoes: [],
  periodo_inicio: '',
  periodo_fim: '',
})

const enviando = ref(false)
const erro = ref<string | null>(null)
const job = ref<ColetaJob | null>(null)
const resultado = ref<HTMLElement | null>(null)
let timer: number | null = null
let tentativas = 0

const emAndamento = computed(() => job.value?.status === 'em_andamento')
const progresso = computed(() => {
  if (!job.value || job.value.estacoes_total === 0) return 0
  return Math.round((job.value.estacoes_processadas / job.value.estacoes_total) * 100)
})
const rotuloStatus = computed(() => {
  switch (job.value?.status) {
    case 'em_andamento':
      return 'Coleta em andamento'
    case 'concluida':
      return 'Coleta concluída'
    case 'erro':
      return 'Falha na coleta'
    default:
      return '—'
  }
})
const tomStatus = computed<'success' | 'danger' | 'info' | 'unknown'>(() => {
  switch (job.value?.status) {
    case 'concluida':
      return 'success'
    case 'erro':
      return 'danger'
    case 'em_andamento':
      return 'info'
    default:
      return 'unknown'
  }
})

onMounted(() => {
  estacoes.carregar()
})

onUnmounted(pararPolling)

function pararPolling(): void {
  if (timer !== null) {
    window.clearTimeout(timer)
    timer = null
  }
}

// @id FUN-TS-UI-039 | @categoria UI | @catalogo FUNCOES.md
async function consultar(jobId: string): Promise<void> {
  try {
    const atual = await api.statusColeta(jobId)
    job.value = atual
    if (atual.status === 'em_andamento') {
      tentativas += 1
      if (tentativas < 240) {
        timer = window.setTimeout(() => void consultar(jobId), 2500)
      } else {
        erro.value = 'A coleta demorou mais que o esperado. Consulte a tela de logs.'
      }
    }
  } catch (e) {
    erro.value = e instanceof ApiProblem ? e.message : 'Falha ao consultar o andamento da coleta.'
  }
}

// @id FUN-TS-UI-022 | @categoria UI | @catalogo FUNCOES.md
async function solicitar(): Promise<void> {
  pararPolling()
  enviando.value = true
  erro.value = null
  job.value = null
  tentativas = 0
  try {
    const resposta = await api.coletarNiveis({
      estacoes: filtro.estacoes,
      periodo_inicio: filtro.periodo_inicio || null,
      periodo_fim: filtro.periodo_fim || null,
    })
    job.value = resposta
    await nextTick()
    resultado.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    if (resposta.status === 'em_andamento') {
      timer = window.setTimeout(() => void consultar(resposta.job_id), 2000)
    }
  } catch (e) {
    erro.value = e instanceof ApiProblem ? e.message : 'Não foi possível solicitar a coleta.'
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="space-y-4 sm:space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Coleta de níveis (ANA)</h1>
      <p class="text-sm text-ink-muted">
        Busca as leituras mais recentes da ANA e grava no banco do sistema.
      </p>
    </header>

    <section
      class="rounded-lg border border-dashed border-ink-muted/40 bg-surface-muted/40 p-4 text-sm text-ink-muted"
    >
      A coleta usa a API REST da ANA, que disponibiliza <strong>os últimos 30 dias</strong> de
      leituras. O período abaixo é opcional e apenas filtra as leituras retornadas. As leituras
      novas são gravadas no banco da aplicação e aparecem no mapa.
    </section>

    <form
      class="grid gap-4 rounded-lg border border-edge bg-surface-elevated p-4 sm:grid-cols-2"
      @submit.prevent="solicitar"
    >
      <div>
        <label for="periodo_inicio" class="mb-1 block text-sm font-medium">
          Período — início (opcional)
        </label>
        <input
          id="periodo_inicio"
          v-model="filtro.periodo_inicio"
          type="date"
          :disabled="emAndamento"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary disabled:opacity-60"
        />
      </div>
      <div>
        <label for="periodo_fim" class="mb-1 block text-sm font-medium">
          Período — fim (opcional)
        </label>
        <input
          id="periodo_fim"
          v-model="filtro.periodo_fim"
          type="date"
          :disabled="emAndamento"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary disabled:opacity-60"
        />
      </div>

      <div class="sm:col-span-2">
        <label for="estacoes" class="mb-1 block text-sm font-medium">
          Estações (deixe vazio para todas as telemétricas)
        </label>
        <select
          id="estacoes"
          v-model="filtro.estacoes"
          multiple
          size="6"
          :disabled="emAndamento"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary disabled:opacity-60"
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
        <BaseButton tipo="submit" :desabilitado="enviando || emAndamento">
          {{ enviando ? 'Solicitando…' : emAndamento ? 'Coleta em andamento…' : 'Solicitar coleta' }}
        </BaseButton>
      </div>
    </form>

    <p v-if="erro" role="alert" class="rounded bg-danger/10 px-3 py-2 text-sm text-danger">
      {{ erro }}
    </p>

    <section
      v-if="job"
      ref="resultado"
      class="space-y-4 rounded-lg border border-edge bg-surface-elevated p-4"
      aria-live="polite"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :tom="tomStatus" :label="rotuloStatus" />
          <span class="text-xs text-ink-muted">job {{ job.job_id }}</span>
        </div>
        <span class="text-xs text-ink-muted">
          {{ job.estacoes_processadas }}/{{ job.estacoes_total }} estações
        </span>
      </div>

      <div v-if="emAndamento">
        <div
          class="h-2 overflow-hidden rounded-full bg-surface-muted"
          role="progressbar"
          :aria-valuenow="progresso"
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="Progresso da coleta"
        >
          <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${progresso}%` }" />
        </div>
        <p class="mt-2 text-xs text-ink-muted">
          Consultando a ANA em lotes de 10 estações. Isso pode levar alguns minutos.
        </p>
      </div>

      <dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt class="text-xs text-ink-muted">Leituras recebidas</dt>
          <dd class="font-semibold tabular-nums">{{ job.leituras }}</dd>
        </div>
        <div>
          <dt class="text-xs text-ink-muted">Novas</dt>
          <dd class="font-semibold tabular-nums text-success">{{ job.inseridas }}</dd>
        </div>
        <div>
          <dt class="text-xs text-ink-muted">Já existentes</dt>
          <dd class="font-semibold tabular-nums">{{ job.ignoradas }}</dd>
        </div>
        <div>
          <dt class="text-xs text-ink-muted">Janela retornada</dt>
          <dd class="font-semibold">
            <template v-if="job.janela.inicio && job.janela.fim">
              {{ job.janela.inicio }} a {{ job.janela.fim }}
            </template>
            <template v-else>—</template>
          </dd>
        </div>
      </dl>

      <p
        v-if="job.mensagem"
        class="rounded px-3 py-2 text-sm"
        :class="
          job.status === 'erro'
            ? 'bg-danger/10 text-danger'
            : job.status === 'concluida'
              ? 'bg-warning/10 text-warning'
              : 'bg-surface-muted text-ink-muted'
        "
      >
        {{ job.mensagem }}
      </p>

      <p v-if="job.status === 'concluida' && job.inseridas > 0" class="text-sm text-success">
        Leituras gravadas. Os níveis atuais já aparecem no
        <RouterLink :to="{ name: 'mapa' }" class="underline">mapa</RouterLink>.
      </p>
    </section>
  </div>
</template>
