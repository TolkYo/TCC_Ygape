<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

import RiverMap from '@/components/map/RiverMap.vue'
import RouteSummary from '@/components/route/RouteSummary.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useEstacoesStore } from '@/stores/estacoes'
import { useRotaStore } from '@/stores/rota'
import { useSessionStore } from '@/stores/session'

const estacoes = useEstacoesStore()
const rota = useRotaStore()
const session = useSessionStore()

onMounted(() => {
  estacoes.carregar()
})

const podeCalcular = computed(() => {
  const { origem_nome, destino_nome } = rota.parametros
  return Boolean(origem_nome) && Boolean(destino_nome) && origem_nome !== destino_nome
})

const rotuloSalvar = computed(() => {
  if (rota.idSalvo !== null) return 'Rota salva no histórico'
  if (rota.salvando) return 'Salvando…'
  return 'Salvar no histórico'
})
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Nova rota</h1>
      <p class="text-sm text-ink-muted">
        Informe origem, destino e parâmetros da embarcação para calcular a rota navegável.
      </p>
    </header>

    <form
      class="grid gap-4 rounded-lg border border-edge bg-surface-elevated p-4 sm:grid-cols-2 lg:grid-cols-3"
      @submit.prevent="rota.calcular()"
    >
      <div>
        <label for="origem" class="mb-1 block text-sm font-medium">Origem</label>
        <select
          id="origem"
          v-model="rota.parametros.origem_nome"
          required
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        >
          <option value="" disabled>Selecione…</option>
          <option
            v-for="estacao in estacoes.itens"
            :key="estacao.codigo_estacao"
            :value="estacao.nome_estacao"
          >
            {{ estacao.nome_estacao }}
          </option>
        </select>
      </div>

      <div>
        <label for="destino" class="mb-1 block text-sm font-medium">Destino</label>
        <select
          id="destino"
          v-model="rota.parametros.destino_nome"
          required
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        >
          <option value="" disabled>Selecione…</option>
          <option
            v-for="estacao in estacoes.itens"
            :key="estacao.codigo_estacao"
            :value="estacao.nome_estacao"
          >
            {{ estacao.nome_estacao }}
          </option>
        </select>
      </div>

      <div class="flex items-end">
        <BaseButton variante="secundaria" class="w-full" @click="rota.inverter()">
          Inverter origem/destino
        </BaseButton>
      </div>

      <div>
        <label for="calado" class="mb-1 block text-sm font-medium">Calado (m)</label>
        <input
          id="calado"
          v-model.number="rota.parametros.calado_m"
          type="number"
          min="0.5"
          max="6"
          step="0.1"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>

      <div>
        <label for="margem" class="mb-1 block text-sm font-medium">Margem de segurança (m)</label>
        <input
          id="margem"
          v-model.number="rota.parametros.margem_seguranca_m"
          type="number"
          min="0"
          max="3"
          step="0.1"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>

      <div>
        <label for="velocidade" class="mb-1 block text-sm font-medium">Velocidade (km/h)</label>
        <input
          id="velocidade"
          v-model.number="rota.parametros.velocidade_embarcacao_kmh"
          type="number"
          min="6"
          max="35"
          step="1"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>

      <div class="sm:col-span-2 lg:col-span-3">
        <BaseButton tipo="submit" :desabilitado="!podeCalcular || rota.calculando">
          {{ rota.calculando ? 'Calculando…' : 'Calcular rota' }}
        </BaseButton>
      </div>
    </form>

    <p v-if="rota.erro" role="alert" class="rounded bg-danger/10 px-3 py-2 text-sm text-danger">
      {{ rota.erro }}
    </p>

    <div v-if="rota.resultado" class="space-y-4">
      <div class="grid gap-4 lg:grid-cols-[1fr_360px]">
        <RiverMap :estacoes="estacoes.itens" :rota="rota.resultado" altura="60vh" />
        <RouteSummary :resultado="rota.resultado" />
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <BaseButton
          v-if="session.autenticado"
          :desabilitado="rota.salvando || rota.idSalvo !== null"
          @click="rota.salvar()"
        >
          {{ rotuloSalvar }}
        </BaseButton>
        <p v-else class="text-sm text-ink-muted">
          <RouterLink
            :to="{ name: 'login', query: { redirect: $route.fullPath } }"
            class="text-primary underline"
          >
            Entre na sua conta
          </RouterLink>
          para salvar a rota no histórico.
        </p>
      </div>

      <p v-if="rota.salvoLocal" role="status" class="text-sm text-warning">
        Sem conexão: a rota foi guardada localmente e será enviada na próxima sincronização.
      </p>
    </div>

    <section
      v-else
      class="rounded-lg border border-dashed border-edge p-8 text-center text-sm text-ink-muted"
    >
      Defina origem e destino e clique em “Calcular rota” para ver a rota no mapa.
    </section>
  </div>
</template>
