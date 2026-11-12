<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import RiverMap from '@/components/map/RiverMap.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useEstacoesStore } from '@/stores/estacoes'
import type { Estacao } from '@/types/api'

type Aba = 'mapa' | 'estacoes'

const estacoes = useEstacoesStore()
const busca = ref('')
const selecionada = ref<Estacao | null>(null)
const aba = ref<Aba>('mapa')
const mapa = ref<InstanceType<typeof RiverMap> | null>(null)

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

const rotuloAba = computed(() => (aba.value === 'mapa' ? 'Mapa' : 'Estações'))

// @id FUN-TS-UI-033 | @categoria UI | @catalogo FUNCOES.md
function trocarAba(nova: Aba): void {
  aba.value = nova
  if (nova === 'mapa') {
    nextTick(() => mapa.value?.redimensionar())
  }
}

// @id FUN-TS-UI-034 | @categoria UI | @catalogo FUNCOES.md
function selecionarDaLista(estacao: Estacao): void {
  selecionada.value = estacao
  const estreito = window.matchMedia('(max-width: 1023px)').matches
  if (estreito) {
    aba.value = 'mapa'
  }
  nextTick(() => {
    if (estreito) {
      mapa.value?.redimensionar()
    }
    mapa.value?.centralizar(estacao.latitude, estacao.longitude, 8)
  })
}

// @id FUN-TS-UI-014 | @categoria UI | @catalogo FUNCOES.md
function tomNivel(estacao: Estacao): 'success' | 'warning' | 'unknown' {
  if (estacao.nivel_atual_cm === null) return 'unknown'
  if (estacao.cota_minima_historica_m === null) return 'success'
  return estacao.nivel_atual_cm / 100 <= estacao.cota_minima_historica_m + 0.5
    ? 'warning'
    : 'success'
}
</script>

<template>
  <div class="space-y-4 sm:space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Mapa</h1>
      <p class="text-sm text-ink-muted">
        Estações fluviais monitoradas pela ANA. Selecione uma para ver o nível atual.
      </p>
    </header>

    <div
      role="tablist"
      aria-label="Visualização do mapa"
      class="flex gap-1 rounded-lg border border-edge bg-surface-elevated p-1 lg:hidden"
    >
      <button
        id="aba-mapa"
        type="button"
        role="tab"
        :aria-selected="aba === 'mapa'"
        aria-controls="painel-mapa"
        class="min-h-11 flex-1 rounded px-3 text-sm font-medium"
        :class="aba === 'mapa' ? 'bg-primary text-white' : 'text-ink-muted hover:bg-surface-muted'"
        @click="trocarAba('mapa')"
      >
        Mapa
      </button>
      <button
        id="aba-estacoes"
        type="button"
        role="tab"
        :aria-selected="aba === 'estacoes'"
        aria-controls="painel-estacoes"
        class="min-h-11 flex-1 rounded px-3 text-sm font-medium"
        :class="
          aba === 'estacoes' ? 'bg-primary text-white' : 'text-ink-muted hover:bg-surface-muted'
        "
        @click="trocarAba('estacoes')"
      >
        Estações
        <span class="ml-1 text-xs font-normal opacity-80">{{ filtradas.length }}</span>
      </button>
    </div>

    <p class="text-xs text-ink-muted lg:hidden" aria-live="polite">
      Exibindo: <span class="font-medium text-ink">{{ rotuloAba }}</span>
    </p>

    <div class="grid min-w-0 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside
        id="painel-estacoes"
        role="tabpanel"
        aria-labelledby="aba-estacoes"
        class="min-w-0 space-y-3 lg:block"
        :class="aba === 'estacoes' ? 'block' : 'hidden'"
      >
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
          class="max-h-[52vh] space-y-1 overflow-y-auto rounded-lg border border-edge bg-surface-elevated p-2 lg:max-h-[60vh]"
          aria-label="Lista de estações"
        >
          <li v-for="estacao in filtradas" :key="estacao.codigo_estacao">
            <button
              type="button"
              class="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded px-2 py-2 text-left text-sm hover:bg-surface-muted"
              :class="{
                'bg-surface-muted': selecionada?.codigo_estacao === estacao.codigo_estacao,
              }"
              @click="selecionarDaLista(estacao)"
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

      <div
        id="painel-mapa"
        role="tabpanel"
        aria-labelledby="aba-mapa"
        class="min-w-0 lg:block"
        :class="aba === 'mapa' ? 'block' : 'hidden'"
      >
        <RiverMap
          ref="mapa"
          :estacoes="estacoes.itens"
          altura="clamp(20rem, 55vh, 38rem)"
          @selecionar-estacao="selecionada = $event"
        />
      </div>
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
      <dl class="mt-3 grid grid-cols-1 gap-3 text-sm min-[380px]:grid-cols-2 sm:grid-cols-3 sm:gap-4">
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
