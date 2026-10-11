import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RotaSalva, RouteResult } from '@/types/api'

vi.mock('@/services/endpoints', () => ({
  api: {
    calcularRota: vi.fn(),
    salvarRota: vi.fn(),
    listarRotas: vi.fn(),
    obterRota: vi.fn(),
    removerRota: vi.fn(),
  },
}))

import { api } from '@/services/endpoints'
import { ApiProblem } from '@/services/http'

import { useRotaStore } from './rota'

const apiMock = vi.mocked(api)

function rotaSalva(overrides: Partial<RotaSalva> = {}): RotaSalva {
  return {
    id: 1,
    usuario_id: 7,
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
    rota_geojson: null,
    monitorar: false,
    created_at: '2026-10-11 02:39:45',
    ...overrides,
  }
}

function resultado(): RouteResult {
  return {
    rota_id: null,
    origem: 'MANAUS',
    destino: 'ITACOATIARA',
    distancia_total_km: 194.32,
    tempo_total_h: 16.19,
    custo_total: 16.19,
    trechos_criticos: 2,
    profundidade_minima_m: 4.1,
    geojson: { type: 'FeatureCollection', features: [] },
    items: [],
  }
}

describe('store de rota', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('não salva sem resultado calculado', async () => {
    const store = useRotaStore()
    await expect(store.salvar()).resolves.toBeNull()
    expect(apiMock.salvarRota).not.toHaveBeenCalled()
  })

  it('salva a rota calculada e atualiza o histórico', async () => {
    const store = useRotaStore()
    store.parametros = {
      origem_nome: 'MANAUS',
      destino_nome: 'ITACOATIARA',
      calado_m: 3.2,
      margem_seguranca_m: 0.5,
      velocidade_embarcacao_kmh: 12,
    }
    store.resultado = resultado()
    apiMock.salvarRota.mockResolvedValue(rotaSalva())

    const salva = await store.salvar()

    expect(apiMock.salvarRota).toHaveBeenCalledWith({
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
      geojson: { type: 'FeatureCollection', features: [] },
      monitorar: false,
    })
    expect(salva?.id).toBe(1)
    expect(store.idSalvo).toBe(1)
    expect(store.historico).toHaveLength(1)
  })

  it('registra erro quando o salvamento falha', async () => {
    const store = useRotaStore()
    store.resultado = resultado()
    apiMock.salvarRota.mockRejectedValue(new ApiProblem('bad', 'sem permissão', 403))

    await expect(store.salvar()).resolves.toBeNull()
    expect(store.erro).toBe('sem permissão')
    expect(store.idSalvo).toBeNull()
  })

  it('carrega o histórico do usuário', async () => {
    const store = useRotaStore()
    apiMock.listarRotas.mockResolvedValue({ items: [rotaSalva(), rotaSalva({ id: 2 })], total: 2 })

    await store.carregarHistorico()

    expect(store.historico).toHaveLength(2)
    expect(store.erroHistorico).toBeNull()
  })

  it('remove uma rota do histórico', async () => {
    const store = useRotaStore()
    store.historico = [rotaSalva(), rotaSalva({ id: 2 })]
    apiMock.removerRota.mockResolvedValue({ id: 1, removida: true })

    await expect(store.remover(1)).resolves.toBe(true)
    expect(store.historico.map((item) => item.id)).toEqual([2])
  })

  it('limpa o resultado e o id salvo ao inverter', () => {
    const store = useRotaStore()
    store.parametros = {
      origem_nome: 'MANAUS',
      destino_nome: 'ITACOATIARA',
      calado_m: 2,
      margem_seguranca_m: 0.5,
      velocidade_embarcacao_kmh: 12,
    }
    store.resultado = resultado()
    store.idSalvo = 9

    store.inverter()

    expect(store.parametros.origem_nome).toBe('ITACOATIARA')
    expect(store.parametros.destino_nome).toBe('MANAUS')
    expect(store.resultado).toBeNull()
    expect(store.idSalvo).toBeNull()
  })
})
