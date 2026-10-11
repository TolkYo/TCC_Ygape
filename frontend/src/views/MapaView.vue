<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import RiverMap from '@/components/map/RiverMap.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useEstacoesStore } from '@/stores/estacoes'
import type { Estacao } from '@/types/api'

const estacoes = useEstacoesStore()
const busca = ref('')
const selecionada = ref<Estacao | null>(null)

onMounted(() => {
  estacoes.carregar()
})

const filtradas = computed(() => {
  const termo = busca.value.trim().toLowerCase()
  if (!termo) {
    return estacoes.itens
  }
  return estacoes.itens.filter((estacao) =>
    [estacao.nome_estacao, estacao.nome_rio, estacao.municipio].some((valor) =>
      valor?.toLowerCase().includes(termo),
    ),
  )
})

function tomNivel(estacao: Estacao): 'success' | 'warning' | 'unknown' {
  if (estacao.nivel_atual_cm === null) return 'unknown'
  if (estacao.cota_minima_historica_m === null) return 'success'
  return estacao.nivel_atual_cm / 100 <= estacao.cota_minima_historica_m + 0.5
    ? 'warning'
    : 'success'
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Mapa</h1>
      <p class="text-sm text-ink-muted">
        Estações fluviais monitoradas pela ANA. Selecione uma para ver o nível atual.
      </p>
    </header>

    <div class="grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside class="space-y-3">
        <div>
          <label for="busca-estacoes" class="mb-1 block text-sm font-medium">
            Buscar estação
          </label>
          <input
            id="busca-estacoes"
            v-model="busca"
            type="search"
            placeholder="Nome, rio ou município"
            class="w-full rounded border border-edge bg-surface-elevated px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
          />
        </div>

      <p v-if="estacoes.carregando" class="text-sm text-ink-muted">Carregando estações…</p>
      <p v-else-if="estacoes.erro" role="alert" class="text-sm text-danger">
        {{ estacoes.erro }}
      </p>
      <p v-else-if="estacoes.doCache" role="status" class="text-xs text-warning">
        Estações carregadas do cache local (podem estar desatualizadas).
      </p>

        <ul
          v-else
          class="max-h-[60vh] space-y-1 overflow-y-auto rounded-lg border border-edge bg-surface-elevated p-2"
          aria-label="Lista de estações"
        >
          <li v-for="estacao in filtradas" :key="estacao.codigo_estacao">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-surface-muted"
              :class="{
                'bg-surface-muted': selecionada?.codigo_estacao === estacao.codigo_estacao,
              }"
              @click="selecionada = estacao"
            >
              <span class="min-w-0">
                <span class="block truncate font-medium">{{ estacao.nome_estacao }}</span>
                <span class="block truncate text-xs text-ink-muted">
                  {{ estacao.nome_rio ?? '—' }}
                </span>
              </span>
              <StatusBadge
                :tom="tomNivel(estacao)"
                :label="
                  estacao.nivel_atual_cm === null ? 's/ dado' : `${estacao.nivel_atual_cm} cm`
                "
              />
            </button>
          </li>
          <li v-if="!filtradas.length" class="px-2 py-3 text-sm text-ink-muted">
            Nenhuma estação encontrada.
          </li>
        </ul>
      </aside>

      <RiverMap
        :estacoes="estacoes.itens"
        altura="60vh"
        @selecionar-estacao="selecionada = $event"
      />
    </div>

    <section
      v-if="selecionada"
      class="rounded-lg border border-edge bg-surface-elevated p-4"
      aria-live="polite"
    >
      <h2 class="text-lg font-semibold">{{ selecionada.nome_estacao }}</h2>
      <p class="text-sm text-ink-muted">
        {{ selecionada.nome_rio ?? 'Rio não informado' }} ·
        {{ selecionada.municipio ?? 'Município não informado' }}
      </p>
      <dl class="mt-3 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
        <div>
          <dt class="text-xs text-ink-muted">Nível atual</dt>
          <dd class="font-semibold tabular-nums">
            {{ selecionada.nivel_atual_cm === null ? '—' : `${selecionada.nivel_atual_cm} cm` }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-ink-muted">Mínima histórica</dt>
          <dd class="font-semibold tabular-nums">
            {{
              selecionada.cota_minima_historica_m === null
                ? '—'
                : `${selecionada.cota_minima_historica_m} m`
            }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-ink-muted">Atualizado em</dt>
          <dd class="font-semibold">{{ selecionada.atualizado_em ?? '—' }}</dd>
        </div>
      </dl>
    </section>
  </div>
</template>
