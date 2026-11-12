import { db, type RotaPendente, type SnapshotArmazenado } from '@/db'
import type { Estacao, RotaSalva, SalvarRotaInput, SnapshotGrafo } from '@/types/api'

const CHAVE_ULTIMA_SINCRONIZACAO = 'ultima_sincronizacao'

// @id FUN-TS-CACHE-001 | @categoria CACHE | @catalogo FUNCOES.md
export async function guardarEstacoes(itens: Estacao[]): Promise<void> {
  await db.transaction('rw', db.estacoes, async () => {
    await db.estacoes.clear()
    await db.estacoes.bulkPut(itens)
  })
}

// @id FUN-TS-CACHE-002 | @categoria CACHE | @catalogo FUNCOES.md
export function lerEstacoes(): Promise<Estacao[]> {
  return db.estacoes.toArray()
}

// @id FUN-TS-CACHE-003 | @categoria CACHE | @catalogo FUNCOES.md
export async function guardarRotas(itens: RotaSalva[]): Promise<void> {
  await db.transaction('rw', db.rotas, async () => {
    await db.rotas.clear()
    await db.rotas.bulkPut(itens)
  })
}

// @id FUN-TS-CACHE-004 | @categoria CACHE | @catalogo FUNCOES.md
export function lerRotas(): Promise<RotaSalva[]> {
  return db.rotas.orderBy('created_at').reverse().toArray()
}

// @id FUN-TS-CACHE-005 | @categoria CACHE | @catalogo FUNCOES.md
export function enfileirarRota(payload: SalvarRotaInput): Promise<number> {
  return db.pendentes.add({ payload, criado_em: new Date().toISOString() })
}

// @id FUN-TS-CACHE-006 | @categoria CACHE | @catalogo FUNCOES.md
export function lerPendentes(): Promise<RotaPendente[]> {
  return db.pendentes.orderBy('id').toArray()
}

// @id FUN-TS-CACHE-007 | @categoria CACHE | @catalogo FUNCOES.md
export function removerPendente(id: number): Promise<void> {
  return db.pendentes.delete(id)
}

// @id FUN-TS-CACHE-008 | @categoria CACHE | @catalogo FUNCOES.md
export function contarPendentes(): Promise<number> {
  return db.pendentes.count()
}

// @id FUN-TS-CACHE-009 | @categoria CACHE | @catalogo FUNCOES.md
export async function guardarUltimaSincronizacao(valor: string): Promise<void> {
  await db.meta.put({ chave: CHAVE_ULTIMA_SINCRONIZACAO, valor })
}

// @id FUN-TS-CACHE-010 | @categoria CACHE | @catalogo FUNCOES.md
export async function lerUltimaSincronizacao(): Promise<string | null> {
  const registro = await db.meta.get(CHAVE_ULTIMA_SINCRONIZACAO)
  return registro?.valor ?? null
}

// @id FUN-TS-CACHE-011 | @categoria CACHE | @catalogo FUNCOES.md
export async function limparCache(): Promise<void> {
  await db.transaction('rw', db.estacoes, db.rotas, db.pendentes, db.meta, db.grafo, async () => {
    await Promise.all([
      db.estacoes.clear(),
      db.rotas.clear(),
      db.pendentes.clear(),
      db.meta.clear(),
      db.grafo.clear(),
    ])
  })
}

// @id FUN-TS-CACHE-012 | @categoria CACHE | @catalogo FUNCOES.md
export async function guardarSnapshot(dados: SnapshotGrafo, geradoEm: string): Promise<void> {
  await db.grafo.put({ chave: 'atual', gerado_em: geradoEm, dados })
}

// @id FUN-TS-CACHE-013 | @categoria CACHE | @catalogo FUNCOES.md
export function lerSnapshot(): Promise<SnapshotArmazenado | undefined> {
  return db.grafo.get('atual')
}
