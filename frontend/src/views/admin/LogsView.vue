<script setup lang="ts">
import { onMounted, ref } from 'vue'

import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { api } from '@/services/endpoints'
import { ApiProblem } from '@/services/http'
import type { LogEvento } from '@/types/api'
import { formatarDataHora } from '@/utils/formato'

const eventos = ref<LogEvento[]>([])
const carregando = ref(false)
const erro = ref<string | null>(null)

const TONS: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'unknown'> = {
  login: 'info',
  perfil_atualizado: 'info',
  usuario_criado: 'success',
  usuario_desativado: 'warning',
  rota_salva: 'success',
}

async function carregar(): Promise<void> {
  carregando.value = true
  erro.value = null
  try {
    eventos.value = (await api.listarLogs()).items
  } catch (e) {
    erro.value =
      e instanceof ApiProblem ? e.message : 'Falha ao carregar os logs de auditoria.'
  } finally {
    carregando.value = false
  }
}

function tom(tipo: string): 'success' | 'warning' | 'danger' | 'info' | 'unknown' {
  return TONS[tipo] ?? 'unknown'
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Logs de auditoria</h1>
        <p class="text-sm text-ink-muted">Eventos recentes da aplicação (login, usuários, rotas).</p>
      </div>
      <BaseButton variante="secundaria" :desabilitado="carregando" @click="carregar">
        {{ carregando ? 'Atualizando…' : 'Atualizar' }}
      </BaseButton>
    </header>

    <p v-if="erro" role="alert" class="rounded bg-danger/10 px-3 py-2 text-sm text-danger">
      {{ erro }}
    </p>

    <p v-if="carregando && !eventos.length" class="text-sm text-ink-muted">Carregando eventos…</p>

    <div v-else-if="eventos.length" class="overflow-x-auto rounded-lg border border-edge">
      <table class="w-full border-collapse text-sm">
        <thead class="bg-surface-muted text-left">
          <tr>
            <th class="px-3 py-2 font-medium">Data/hora</th>
            <th class="px-3 py-2 font-medium">Tipo</th>
            <th class="px-3 py-2 font-medium">Usuário</th>
            <th class="px-3 py-2 font-medium">Detalhe</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="evento in eventos" :key="evento.id" class="border-t border-edge">
            <td class="whitespace-nowrap px-3 py-2 text-ink-muted">
              {{ formatarDataHora(evento.data_hora) }}
            </td>
            <td class="px-3 py-2">
              <StatusBadge :tom="tom(evento.tipo)" :label="evento.tipo" />
            </td>
            <td class="px-3 py-2 text-ink-muted">{{ evento.usuario_id ?? '—' }}</td>
            <td class="px-3 py-2">{{ evento.detalhe ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p
      v-else
      class="rounded-lg border border-dashed border-edge p-8 text-center text-sm text-ink-muted"
    >
      Nenhum evento registrado ainda.
    </p>
  </div>
</template>
