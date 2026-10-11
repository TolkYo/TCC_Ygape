import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  contarPendentes,
  enfileirarRota,
  guardarEstacoes,
  guardarRotas,
  guardarUltimaSincronizacao,
  lerPendentes,
  lerUltimaSincronizacao,
  removerPendente,
} from '@/services/cache'
import { api } from '@/services/endpoints'
import type { SalvarRotaInput } from '@/types/api'

export const useOfflineStore = defineStore('offline', () => {
  const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
  const sincronizando = ref(false)
  const ultimaSincronizacao = ref<string | null>(null)
  const pendentes = ref(0)
  const erro = ref<string | null>(null)

  async function atualizarContadores(): Promise<void> {
    pendentes.value = await contarPendentes()
    ultimaSincronizacao.value = await lerUltimaSincronizacao()
  }

  async function enfileirar(payload: SalvarRotaInput): Promise<void> {
    await enfileirarRota(payload)
    pendentes.value = await contarPendentes()
  }

  async function enviarPendentes(): Promise<void> {
    const fila = await lerPendentes()
    for (const item of fila) {
      if (item.id === undefined) continue
      try {
        await api.salvarRota(item.payload)
        await removerPendente(item.id)
      } catch {
        break
      }
    }
  }

  async function sincronizar(): Promise<void> {
    if (!online.value || sincronizando.value) {
      return
    }
    sincronizando.value = true
    erro.value = null
    try {
      const estacoes = await api.listarEstacoes()
      await guardarEstacoes(estacoes.items)

      await enviarPendentes()

      try {
        const rotas = await api.listarRotas()
        await guardarRotas(rotas.items)
      } catch {
        // Usuário anônimo: o histórico exige autenticação.
      }

      const agora = new Date().toISOString()
      await guardarUltimaSincronizacao(agora)
      ultimaSincronizacao.value = agora
    } catch (e) {
      erro.value = e instanceof Error ? e.message : 'Falha na sincronização.'
    } finally {
      pendentes.value = await contarPendentes()
      sincronizando.value = false
    }
  }

  function registarListeners(): () => void {
    const aoOnline = (): void => {
      online.value = true
      void sincronizar()
    }
    const aoOffline = (): void => {
      online.value = false
    }
    window.addEventListener('online', aoOnline)
    window.addEventListener('offline', aoOffline)
    return () => {
      window.removeEventListener('online', aoOnline)
      window.removeEventListener('offline', aoOffline)
    }
  }

  return {
    online,
    sincronizando,
    ultimaSincronizacao,
    pendentes,
    erro,
    atualizarContadores,
    enfileirar,
    sincronizar,
    registarListeners,
  }
})
