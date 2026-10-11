import { describe, expect, it } from 'vitest'

import { calcularOffline } from './roteador'
import type { SnapshotGrafo } from '@/types/api'

// Cadeia 1-2-3-4. A na aresta 1, B na aresta 3. A aresta 2 (2-3) tem pouca profundidade.
const snap: SnapshotGrafo = {
  gerado_em: '2026-10-11T00:00:00',
  area: 'teste',
  total_nos: 4,
  total_arestas: 3,
  nos: [
    [1, -60.0, -3.0],
    [2, -60.1, -3.0],
    [3, -60.2, -3.0],
    [4, -60.3, -3.0],
  ],
  // [fid, origem, destino, distancia_km, profundidade_m]
  arestas: [
    [1, 1, 2, 10, 5],
    [2, 2, 3, 10, 1],
    [3, 3, 4, 10, 5],
  ],
  estacoes: [
    ['A', 1],
    ['B', 3],
  ],
}

describe('roteador offline (Dijkstra sobre o snapshot)', () => {
  it('encontra a rota quando o calado é compatível', () => {
    const rota = calcularOffline(snap, 'A', 'B', 0.5, 0, 12)
    expect(rota).not.toBeNull()
    // inclui a aresta de origem (1) e a de destino (3), como no backend
    expect(rota?.items.map((i) => i.fid)).toEqual([1, 2, 3])
    expect(rota?.distancia_total_km).toBe(30)
    expect(rota?.profundidade_minima_m).toBe(1)
    expect(rota?.geojson.features).toHaveLength(3)
  })

  it('retorna null quando um trecho é intransitável', () => {
    // required = 2 + 1 = 3; a aresta 2 tem profundidade 1 -> caminho bloqueado
    const rota = calcularOffline(snap, 'A', 'B', 2, 1, 12)
    expect(rota).toBeNull()
  })

  it('trata a mesma estação de origem e destino', () => {
    const sozinho: SnapshotGrafo = { ...snap, estacoes: [['A', 1]] }
    const rota = calcularOffline(sozinho, 'A', 'A', 1, 0.5, 12)
    expect(rota?.items.map((i) => i.fid)).toEqual([1])
  })

  it('retorna null para estação inexistente', () => {
    expect(calcularOffline(snap, 'A', 'Z', 1, 0, 12)).toBeNull()
  })
})
