import { defineStore } from 'pinia'
import { ref } from 'vue'

import { guardarEstacoes, lerEstacoes as lerEstacoesCache } from '@/services/cache'
import { api } from '@/services/endpoints'
import type { Estacao } from '@/types/api'

export const useEstacoesStore = defineStore('estacoes', () => {
  const itens = ref<Estacao[]>([])
  const carregando = ref(false)
  const erro = ref<string | null>(null)
  const carregado = ref(false)
  const doCache = ref(false)

  async function carregar(forcar = false): Promise<void> {
    if (carregado.value && !forcar) {
      return
    }
    carregando.value = true
    erro.value = null
    try {
      const resposta = await api.listarEstacoes()
      itens.value = resposta.items
      carregado.value = true
      doCache.value = false
      void guardarEstacoes(resposta.items).catch(() => undefined)
    } catch {
      const cache = await lerEstacoesCache()
      if (cache.length) {
        itens.value = cache
        carregado.value = true
        doCache.value = true
      } else {
        erro.value = 'Não foi possível carregar as estações. Verifique a conexão com a API.'
      }
    } finally {
      carregando.value = false
    }
  }

  return { itens, carregando, erro, carregado, doCache, carregar }
})
