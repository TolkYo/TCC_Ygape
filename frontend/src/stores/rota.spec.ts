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
    monitorarRota: vi.fn(),
    listarAlteracoes: vi.fn(),
  },
}))

import { api } from '@/services/endpoints'
import { guardarSnapshot, limparCache } from '@/services/cache'
import { ApiProblem } from '@/services/http'

import { useEstacoesStore } from './estacoes'
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

  it('ativa o monitoramento de uma rota', async () => {
    const store = useRotaStore()
    store.historico = [rotaSalva({ id: 1, monitorar: false })]
    apiMock.monitorarRota.mockResolvedValue({
      rota_id: 1,
      monitorar: true,
      estacao_referencia: '16030000',
      nivel_baseline_cm: 500,
      limiar_variacao_cm: 30,
      cooldown_min: 30,
    })

    const resultado = await store.monitorar(1, true)

    expect(apiMock.monitorarRota).toHaveBeenCalledWith(1, true)
    expect(resultado?.monitorar).toBe(true)
    expect(store.historico[0]?.monitorar).toBe(true)
  })

  it('calcula offline quando a API está inacessível e há snapshot', async () => {
    await limparCache()
    const store = useRotaStore()
    const est = useEstacoesStore()
    est.itens = [
      { codigo_estacao: 'A', nome_estacao: 'ORIGEM' } as never,
      { codigo_estacao: 'B', nome_estacao: 'DESTINO' } as never,
    ]
    store.parametros = {
      origem_nome: 'ORIGEM',
      destino_nome: 'DESTINO',
      calado_m: 0.5,
      margem_seguranca_m: 0,
      velocidade_embarcacao_kmh: 12,
    }
    await guardarSnapshot(
      {
        gerado_em: 'x',
        area: 't',
        total_nos: 2,
        total_arestas: 1,
        nos: [
          [1, -60, -3],
          [2, -60.1, -3],
        ],
        arestas: [[1, 1, 2, 10, 5]],
        estacoes: [
          ['A', 1],
          ['B', 1],
        ],
      },
      'x',
    )
    apiMock.calcularRota.mockRejectedValue(new TypeError('rede fora'))

    await store.calcular()

    expect(store.calculadoOffline).toBe(true)
    expect(store.resultado?.distancia_total_km).toBe(10)
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
