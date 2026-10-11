<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import RiverMap from '@/components/map/RiverMap.vue'
import RouteSummary from '@/components/route/RouteSummary.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useEstacoesStore } from '@/stores/estacoes'
import { useRotaStore } from '@/stores/rota'
import type { AlteracaoRota, RotaSalva, RouteResult } from '@/types/api'
import { formatarDataHora, formatarNumero } from '@/utils/formato'

const rota = useRotaStore()
const estacoes = useEstacoesStore()
const expandida = ref<number | null>(null)
const alteracoesPorRota = ref<Record<number, AlteracaoRota[]>>({})

onMounted(() => {
  rota.carregarHistorico()
  estacoes.carregar()
})

function resultadoDaRota(item: RotaSalva): RouteResult {
  return {
    rota_id: item.id,
    origem: item.origem_nome,
    destino: item.destino_nome,
    distancia_total_km: item.distancia_total_km,
    tempo_total_h: item.tempo_total_h,
    custo_total: item.custo_total,
    trechos_criticos: item.trechos_criticos,
    profundidade_minima_m: item.profundidade_minima_m,
    geojson: item.rota_geojson ?? { type: 'FeatureCollection', features: [] },
    items: [],
  }
}

async function carregarAlteracoes(id: number): Promise<void> {
  alteracoesPorRota.value = { ...alteracoesPorRota.value, [id]: await rota.alteracoes(id) }
}

async function alternar(item: RotaSalva): Promise<void> {
  if (expandida.value === item.id) {
    expandida.value = null
    return
  }
  expandida.value = item.id
  if (item.monitorar) {
    await carregarAlteracoes(item.id)
  }
}

async function alternarMonitoramento(item: RotaSalva): Promise<void> {
  const resultado = await rota.monitorar(item.id, !item.monitorar)
  if (resultado?.monitorar) {
    await carregarAlteracoes(item.id)
  }
}

async function remover(id: number): Promise<void> {
  const ok = await rota.remover(id)
  if (ok && expandida.value === id) {
    expandida.value = null
  }
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Histórico</h1>
      <p class="text-sm text-ink-muted">Rotas salvas pelo usuário autenticado.</p>
    </header>

    <p v-if="rota.carregandoHistorico" class="text-sm text-ink-muted">Carregando rotas…</p>

    <p
      v-else-if="rota.historicoDoCache"
      role="status"
      class="rounded bg-warning/10 px-3 py-2 text-sm text-warning"
    >
      Sem conexão: rotas exibidas a partir do cache local.
    </p>

    <p v-else-if="rota.erroHistorico" role="alert" class="rounded bg-danger/10 px-3 py-2 text-sm text-danger">
      {{ rota.erroHistorico }}
    </p>

    <section
      v-else-if="!rota.historico.length"
      class="rounded-lg border border-dashed border-edge p-8 text-center text-sm text-ink-muted"
    >
      Nenhuma rota salva ainda. Calcule uma rota em
      <RouterLink :to="{ name: 'rota-nova' }" class="text-primary underline">Nova rota</RouterLink>
      e clique em “Salvar no histórico”.
    </section>

    <ul v-else class="space-y-3">
      <li
        v-for="item in rota.historico"
        :key="item.id"
        class="rounded-lg border border-edge bg-surface-elevated"
      >
        <div class="flex flex-wrap items-center justify-between gap-3 p-4">
          <div class="min-w-0">
            <p class="flex flex-wrap items-center gap-2 font-medium">
              {{ item.origem_nome }} → {{ item.destino_nome }}
              <StatusBadge v-if="item.monitorar" tom="info" label="Monitorando" />
            </p>
            <p class="text-xs text-ink-muted">
              {{ formatarDataHora(item.created_at) }} · calado
              {{ formatarNumero(item.calado_m, 1) }} m ·
              {{ formatarNumero(item.distancia_total_km) }} km ·
              {{ formatarNumero(item.tempo_total_h) }} h
            </p>
          </div>
          <div class="flex items-center gap-2">
            <BaseButton variante="secundaria" @click="alternarMonitoramento(item)">
              {{ item.monitorar ? 'Parar de monitorar' : 'Monitorar' }}
            </BaseButton>
            <BaseButton variante="secundaria" @click="alternar(item)">
              {{ expandida === item.id ? 'Ocultar' : 'Detalhes' }}
            </BaseButton>
            <BaseButton variante="perigo" @click="remover(item.id)">Remover</BaseButton>
          </div>
        </div>

        <div v-if="expandida === item.id" class="space-y-3 border-t border-edge p-4">
          <RouteSummary :resultado="resultadoDaRota(item)" />

          <div v-if="item.monitorar">
            <h3 class="mb-1 text-sm font-semibold">Alterações monitoradas</h3>
            <p v-if="!alteracoesPorRota[item.id]?.length" class="text-sm text-ink-muted">
              Sem alterações registradas até agora.
            </p>
            <ul v-else class="space-y-1 text-sm text-ink-muted">
              <li v-for="alt in alteracoesPorRota[item.id]" :key="alt.id">
                {{ formatarDataHora(alt.data_alteracao) }} · {{ alt.motivo }}
                ({{ formatarNumero(alt.variacao_nivel_cm, 0) }} cm ·
                {{ formatarNumero(alt.distancia_total_km) }} km)
              </li>
            </ul>
          </div>

          <RiverMap
            v-if="item.rota_geojson"
            :estacoes="estacoes.itens"
            :rota="resultadoDaRota(item)"
            altura="45vh"
          />
        </div>
      </li>
    </ul>
  </div>
</template>
