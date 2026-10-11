<script setup lang="ts">
import { computed } from 'vue'

import StatusBadge from '@/components/ui/StatusBadge.vue'
import type { RouteResult } from '@/types/api'
import { formatarInteiro, formatarNumero } from '@/utils/formato'

const props = defineProps<{ resultado: RouteResult }>()

const criticos = computed(() => props.resultado.items.filter((item) => !item.transitavel))

const tomProfundidade = computed<'success' | 'warning' | 'danger' | 'unknown'>(() => {
  const valor = props.resultado.profundidade_minima_m
  if (valor === null) return 'unknown'
  if (valor < 2) return 'danger'
  if (valor < 4) return 'warning'
  return 'success'
})
</script>

<template>
  <section
    class="rounded-lg border border-edge bg-surface-elevated p-4"
    aria-label="Resumo da rota"
  >
    <header class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-muted">Resumo da rota</h2>
      <StatusBadge
        :tom="criticos.length ? 'warning' : 'success'"
        :label="`${criticos.length} trecho(s) crítico(s)`"
      />
    </header>

    <dl class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div>
        <dt class="text-xs text-ink-muted">Distância</dt>
        <dd class="text-lg font-semibold tabular-nums">
          {{ formatarNumero(resultado.distancia_total_km) }} km
        </dd>
      </div>
      <div>
        <dt class="text-xs text-ink-muted">Tempo estimado</dt>
        <dd class="text-lg font-semibold tabular-nums">
          {{ formatarNumero(resultado.tempo_total_h) }} h
        </dd>
      </div>
      <div>
        <dt class="text-xs text-ink-muted">Trechos</dt>
        <dd class="text-lg font-semibold tabular-nums">
          {{ formatarInteiro(resultado.items.length) }}
        </dd>
      </div>
      <div>
        <dt class="text-xs text-ink-muted">Profundidade mínima</dt>
        <dd class="mt-1">
          <StatusBadge
            :tom="tomProfundidade"
            :label="
              resultado.profundidade_minima_m === null
                ? 'sem dado'
                : `${formatarNumero(resultado.profundidade_minima_m, 2)} m`
            "
          />
        </dd>
      </div>
    </dl>

    <p v-if="criticos.length" class="mt-4 text-xs text-ink-muted">
      Trechos críticos são aqueles com profundidade inferior ao calado informado mais a margem de
      segurança.
    </p>
  </section>
</template>
