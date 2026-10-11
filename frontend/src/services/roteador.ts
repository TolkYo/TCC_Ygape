import type { GeoJsonFeatureCollection, RouteResult, RouteSegment, SnapshotGrafo } from '@/types/api'

type Aresta = { fid: number; o: number; d: number; dist: number; prof: number | null }

class MinHeap {
  private itens: Array<[number, number]> = []

  get tamanho(): number {
    return this.itens.length
  }

  push(custo: number, no: number): void {
    this.itens.push([custo, no])
    let i = this.itens.length - 1
    while (i > 0) {
      const pai = (i - 1) >> 1
      if (this.itens[pai][0] <= this.itens[i][0]) break
      ;[this.itens[pai], this.itens[i]] = [this.itens[i], this.itens[pai]]
      i = pai
    }
  }

  pop(): [number, number] | undefined {
    const topo = this.itens[0]
    const ultimo = this.itens.pop()
    if (this.itens.length && ultimo) {
      this.itens[0] = ultimo
      let i = 0
      for (;;) {
        const esq = 2 * i + 1
        const dir = 2 * i + 2
        let menor = i
        if (esq < this.itens.length && this.itens[esq][0] < this.itens[menor][0]) menor = esq
        if (dir < this.itens.length && this.itens[dir][0] < this.itens[menor][0]) menor = dir
        if (menor === i) break
        ;[this.itens[i], this.itens[menor]] = [this.itens[menor], this.itens[i]]
        i = menor
      }
    }
    return topo
  }
}

function round(valor: number, digitos: number): number {
  return Number(valor.toFixed(digitos))
}

/**
 * Roteamento offline (RF022) sobre o snapshot do grafo.
 * Mesma regra de custo/transitabilidade do backend: menor caminho por distância,
 * podando arestas com profundidade < calado + margem.
 */
export function calcularOffline(
  snap: SnapshotGrafo,
  origemCodigo: string,
  destinoCodigo: string,
  calado: number,
  margem: number,
  velocidade: number,
): RouteResult | null {
  const arestas = new Map<number, Aresta>()
  const adj = new Map<number, Array<[number, number]>>()
  for (const [fid, o, d, dist, prof] of snap.arestas) {
    arestas.set(fid, { fid, o, d, dist, prof })
    let listaOrigem = adj.get(o)
    if (!listaOrigem) {
      listaOrigem = []
      adj.set(o, listaOrigem)
    }
    listaOrigem.push([d, fid])
    let listaDestino = adj.get(d)
    if (!listaDestino) {
      listaDestino = []
      adj.set(d, listaDestino)
    }
    listaDestino.push([o, fid])
  }

  const estacoes = new Map(snap.estacoes)
  const origemFid = estacoes.get(origemCodigo)
  const destinoFid = estacoes.get(destinoCodigo)
  if (origemFid == null || destinoFid == null) return null

  const coords = new Map<number, [number, number]>()
  for (const [id, lon, lat] of snap.nos) coords.set(id, [lon, lat])

  const required = calado + margem
  let fids: number[]

  if (origemFid === destinoFid) {
    fids = [origemFid]
  } else {
    const oe = arestas.get(origemFid)
    const de = arestas.get(destinoFid)
    if (!oe || !de) return null
    const starts = [oe.o, oe.d]
    const targets = new Set([de.o, de.d])
    const dist = new Map<number, number>()
    const prev = new Map<number, [number, number]>()
    const heap = new MinHeap()
    for (const s of starts) {
      dist.set(s, 0)
      heap.push(0, s)
    }

    let encontrado: number | null = null
    while (heap.tamanho) {
      const [custo, no] = heap.pop()!
      if (custo !== dist.get(no)) continue
      if (targets.has(no)) {
        encontrado = no
        break
      }
      for (const [viz, fid] of adj.get(no) ?? []) {
        const aresta = arestas.get(fid)!
        if (aresta.prof != null && aresta.prof < required) continue
        const candidato = custo + aresta.dist
        if (candidato < (dist.get(viz) ?? Infinity)) {
          dist.set(viz, candidato)
          prev.set(viz, [no, fid])
          heap.push(candidato, viz)
        }
      }
    }
    if (encontrado === null) return null

    fids = []
    let cursor: number = encontrado
    while (!starts.includes(cursor)) {
      const passo = prev.get(cursor)
      if (!passo) return null
      fids.push(passo[1])
      cursor = passo[0]
    }
    fids.reverse()
    if (!fids.includes(origemFid)) fids.unshift(origemFid)
    if (!fids.includes(destinoFid)) fids.push(destinoFid)
    fids = [...new Set(fids)]
  }

  const edges = fids.map((fid) => arestas.get(fid)).filter((a): a is Aresta => a !== undefined)
  const distancia = edges.reduce((soma, edge) => soma + edge.dist, 0)
  const depths = edges.map((edge) => edge.prof).filter((p): p is number => p !== null)

  const features = edges.map((edge) => {
    const a = coords.get(edge.o)
    const b = coords.get(edge.d)
    const linha = a && b ? [[a[0], a[1]], [b[0], b[1]]] : []
    return {
      type: 'Feature' as const,
      properties: { fid: edge.fid, distancia_km: round(edge.dist, 3), profundidade_m: edge.prof },
      geometry: { type: 'LineString', coordinates: linha },
    }
  })
  const geojson: GeoJsonFeatureCollection = { type: 'FeatureCollection', features }

  const items: RouteSegment[] = edges.map((edge) => ({
    no_origem: edge.o,
    no_destino: edge.d,
    fid: edge.fid,
    distancia_km: round(edge.dist, 3),
    profundidade_m: edge.prof,
    transitavel: edge.prof === null || edge.prof >= required,
    tempo_h: round(edge.dist / velocidade, 3),
  }))

  return {
    rota_id: null,
    origem: origemCodigo,
    destino: destinoCodigo,
    distancia_total_km: round(distancia, 3),
    tempo_total_h: round(distancia / velocidade, 3),
    custo_total: round(distancia / velocidade, 3),
    trechos_criticos: items.filter((item) => !item.transitavel).length,
    profundidade_minima_m: depths.length ? Math.min(...depths) : null,
    geojson,
    items,
  }
}
