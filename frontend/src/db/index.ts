import Dexie, { type Table } from 'dexie'

import type { Estacao, RotaSalva, SalvarRotaInput, SnapshotGrafo } from '@/types/api'

export type RotaPendente = {
  id?: number
  payload: SalvarRotaInput
  criado_em: string
}

export type MetaRegistro = {
  chave: string
  valor: string
}

export type SnapshotArmazenado = {
  chave: string
  gerado_em: string
  dados: SnapshotGrafo
}

export class YgapeDatabase extends Dexie {
  estacoes!: Table<Estacao, string>
  rotas!: Table<RotaSalva, number>
  pendentes!: Table<RotaPendente, number>
  meta!: Table<MetaRegistro, string>
  grafo!: Table<SnapshotArmazenado, string>

  constructor() {
    super('ygape-offline')
    this.version(1).stores({
      estacoes: 'codigo_estacao',
      rotas: 'id, created_at',
      pendentes: '++id, criado_em',
      meta: 'chave',
    })
    this.version(2).stores({
      estacoes: 'codigo_estacao',
      rotas: 'id, created_at',
      pendentes: '++id, criado_em',
      meta: 'chave',
      grafo: 'chave',
    })
  }
}

export const db = new YgapeDatabase()
