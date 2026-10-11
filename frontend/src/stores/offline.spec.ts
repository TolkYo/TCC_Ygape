import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/endpoints', () => ({
  api: {
    listarEstacoes: vi.fn(),
    listarRotas: vi.fn(),
    salvarRota: vi.fn(),
  },
}))

import {
  contarPendentes,
  enfileirarRota,
  lerEstacoes,
  lerUltimaSincronizacao,
  limparCache,
} from '@/services/cache'
import { api } from '@/services/endpoints'
import type { Estacao, SalvarRotaInput } from '@/types/api'

import { useOfflineStore } from './offline'

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

function payload(): SalvarRotaInput {
  return {
    origem_nome: 'MANAUS',
    destino_nome: 'ITACOATIARA',
    calado_m: 3.2,
    margem_seguranca_m: 0.5,
    velocidade_embarcacao_kmh: 12,
    distancia_total_km: 194.32,
    tempo_total_h: 16.19,
    custo_total: 16.19,
    trechos_criticos: 2,
    profundidade_minima_m: 4.1,
    geojson: null,
  }
}

describe('store offline', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    await limparCache()
    vi.clearAllMocks()
    apiMock.listarEstacoes.mockResolvedValue({ items: [estacao('14990000')], total: 1 })
    apiMock.listarRotas.mockResolvedValue({ items: [], total: 0 })
    apiMock.salvarRota.mockResolvedValue({ id: 1 } as never)
  })

  it('faz pull das estações e atualiza a data de sincronização', async () => {
    const store = useOfflineStore()

    await store.sincronizar()

    expect(apiMock.listarEstacoes).toHaveBeenCalledOnce()
    expect((await lerEstacoes()).map((item) => item.codigo_estacao)).toEqual(['14990000'])
    expect(await lerUltimaSincronizacao()).not.toBeNull()
    expect(store.sincronizando).toBe(false)
  })

  it('envia rotas pendentes e limpa a fila', async () => {
    const store = useOfflineStore()
    await enfileirarRota(payload())
    await store.atualizarContadores()
    expect(store.pendentes).toBe(1)

    await store.sincronizar()

    expect(apiMock.salvarRota).toHaveBeenCalledOnce()
    expect(await contarPendentes()).toBe(0)
    expect(store.pendentes).toBe(0)
  })

  it('não sincroniza quando offline', async () => {
    const store = useOfflineStore()
    store.online = false

    await store.sincronizar()

    expect(apiMock.listarEstacoes).not.toHaveBeenCalled()
  })

  it('registra erro quando o pull falha', async () => {
    const store = useOfflineStore()
    apiMock.listarEstacoes.mockRejectedValue(new Error('rede fora'))

    await store.sincronizar()

    expect(store.erro).toBe('rede fora')
  })
})
