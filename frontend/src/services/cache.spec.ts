import { beforeEach, describe, expect, it } from 'vitest'

import {
  contarPendentes,
  enfileirarRota,
  guardarEstacoes,
  guardarRotas,
  guardarUltimaSincronizacao,
  lerEstacoes,
  lerPendentes,
  lerRotas,
  lerUltimaSincronizacao,
  limparCache,
  removerPendente,
} from './cache'
import type { Estacao, RotaSalva, SalvarRotaInput } from '@/types/api'

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

function rota(id: number, createdAt: string): RotaSalva {
  return {
    id,
    usuario_id: 1,
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
    created_at: createdAt,
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

describe('camada de cache local (Dexie)', () => {
  beforeEach(async () => {
    await limparCache()
  })

  it('guarda e lê estações', async () => {
    await guardarEstacoes([estacao('14990000'), estacao('15040000')])
    const itens = await lerEstacoes()
    expect(itens.map((item) => item.codigo_estacao).sort()).toEqual(['14990000', '15040000'])
  })

  it('substitui o snapshot de estações a cada gravação', async () => {
    await guardarEstacoes([estacao('14990000')])
    await guardarEstacoes([estacao('15040000')])
    const itens = await lerEstacoes()
    expect(itens.map((item) => item.codigo_estacao)).toEqual(['15040000'])
  })

  it('lista rotas da mais recente para a mais antiga', async () => {
    await guardarRotas([rota(1, '2026-10-01 10:00:00'), rota(2, '2026-10-05 10:00:00')])
    const itens = await lerRotas()
    expect(itens.map((item) => item.id)).toEqual([2, 1])
  })

  it('enfileira, conta e remove rotas pendentes', async () => {
    const id = await enfileirarRota(payload())
    expect(await contarPendentes()).toBe(1)
    expect((await lerPendentes())[0]?.payload.origem_nome).toBe('MANAUS')
    await removerPendente(id)
    expect(await contarPendentes()).toBe(0)
  })

  it('persiste e recupera a data da última sincronização', async () => {
    expect(await lerUltimaSincronizacao()).toBeNull()
    await guardarUltimaSincronizacao('2026-10-11T12:00:00.000Z')
    expect(await lerUltimaSincronizacao()).toBe('2026-10-11T12:00:00.000Z')
  })
})
