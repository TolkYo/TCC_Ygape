import { db, type RotaPendente } from '@/db'
import type { Estacao, RotaSalva, SalvarRotaInput } from '@/types/api'

const CHAVE_ULTIMA_SINCRONIZACAO = 'ultima_sincronizacao'

export async function guardarEstacoes(itens: Estacao[]): Promise<void> {
  await db.transaction('rw', db.estacoes, async () => {
    await db.estacoes.clear()
    await db.estacoes.bulkPut(itens)
  })
}

export function lerEstacoes(): Promise<Estacao[]> {
  return db.estacoes.toArray()
}

export async function guardarRotas(itens: RotaSalva[]): Promise<void> {
  await db.transaction('rw', db.rotas, async () => {
    await db.rotas.clear()
    await db.rotas.bulkPut(itens)
  })
}

export function lerRotas(): Promise<RotaSalva[]> {
  return db.rotas.orderBy('created_at').reverse().toArray()
}

export function enfileirarRota(payload: SalvarRotaInput): Promise<number> {
  return db.pendentes.add({ payload, criado_em: new Date().toISOString() })
}

export function lerPendentes(): Promise<RotaPendente[]> {
  return db.pendentes.orderBy('id').toArray()
}

export function removerPendente(id: number): Promise<void> {
  return db.pendentes.delete(id)
}

export function contarPendentes(): Promise<number> {
  return db.pendentes.count()
}

export async function guardarUltimaSincronizacao(valor: string): Promise<void> {
  await db.meta.put({ chave: CHAVE_ULTIMA_SINCRONIZACAO, valor })
}

export async function lerUltimaSincronizacao(): Promise<string | null> {
  const registro = await db.meta.get(CHAVE_ULTIMA_SINCRONIZACAO)
  return registro?.valor ?? null
}

export async function limparCache(): Promise<void> {
  await db.transaction('rw', db.estacoes, db.rotas, db.pendentes, db.meta, async () => {
    await Promise.all([db.estacoes.clear(), db.rotas.clear(), db.pendentes.clear(), db.meta.clear()])
  })
}
