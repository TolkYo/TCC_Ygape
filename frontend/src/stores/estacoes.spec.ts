import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/endpoints', () => ({
  api: { listarEstacoes: vi.fn() },
}))

import { guardarEstacoes, limparCache } from '@/services/cache'
import { api } from '@/services/endpoints'
import type { Estacao } from '@/types/api'

import { useEstacoesStore } from './estacoes'

const apiMock = vi.mocked(api)

function estacao(codigo: string): Estacao {
  return {
    codigo_estacao: codigo,
    nome_estacao: `Estação ${codigo}`,
    nome_rio: 'RIO NEGRO',
    municipio: 'MANAUS',
    latitude: -3.1,
    longitude: -60,
    cota_minima_historica_m: 2.8,
    nivel_atual_cm: 2603,
    atualizado_em: '2026-10-11T00:00:00Z',
  }
}

describe('store de estações', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    await limparCache()
    vi.clearAllMocks()
  })

  it('carrega da API e marca como online', async () => {
    apiMock.listarEstacoes.mockResolvedValue({ items: [estacao('14990000')], total: 1 })
    const store = useEstacoesStore()

    await store.carregar()

    expect(store.itens).toHaveLength(1)
    expect(store.doCache).toBe(false)
  })

  it('usa o cache local quando a API falha', async () => {
    await guardarEstacoes([estacao('15040000')])
    apiMock.listarEstacoes.mockRejectedValue(new Error('sem rede'))
    const store = useEstacoesStore()

    await store.carregar()

    expect(store.itens.map((item) => item.codigo_estacao)).toEqual(['15040000'])
    expect(store.doCache).toBe(true)
    expect(store.erro).toBeNull()
  })

  it('reporta erro quando falha e não há cache', async () => {
    apiMock.listarEstacoes.mockRejectedValue(new Error('sem rede'))
    const store = useEstacoesStore()

    await store.carregar()

    expect(store.itens).toHaveLength(0)
    expect(store.erro).not.toBeNull()
  })
})
