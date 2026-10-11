export type ApiSuccess<T> = { success: true; data: T }
export type ApiErrorBody = { success: false; error: { code: string; message: string } }
export type ApiEnvelope<T> = ApiSuccess<T> | ApiErrorBody

export type Papel = 'admin' | 'piloto'

export type Usuario = {
  id: number
  nome: string
  email: string
  papel: Papel
}

export type LoginResult = {
  access_token: string
  token_type: string
  expires_in: number
  usuario: Usuario
}

export type UsuarioAdmin = {
  id: number
  nome: string
  email: string
  papel: Papel
  ativo: boolean
  criado_em: string
}

export type ListaUsuarios = { items: UsuarioAdmin[]; total: number }

export type CriarUsuarioInput = {
  nome: string
  email: string
  senha: string
  papel: Papel
}

export type AtualizarUsuarioInput = {
  nome?: string
  senha?: string
  papel?: Papel
  ativo?: boolean
}

export type PerfilUpdateInput = {
  nome?: string
  senha?: string
}

export type ColetaInput = {
  estacoes?: string[]
  periodo_inicio?: string | null
  periodo_fim?: string | null
}

export type LogEvento = {
  id: number
  usuario_id: number | null
  tipo: string
  detalhe: string | null
  data_hora: string
}

export type ListaLogs = { items: LogEvento[]; total: number }

export type Estacao = {
  codigo_estacao: string
  nome_estacao: string
  nome_rio: string | null
  municipio: string | null
  latitude: number
  longitude: number
  cota_minima_historica_m: number | null
  nivel_atual_cm: number | null
  atualizado_em: string | null
}

export type ListaEstacoes = { items: Estacao[]; total: number }

export type GrafoStatus = {
  nos: number
  arestas: number
  portos_associados: number
  area_ativa: string
  ultima_reconstrucao: string | null
  pronto: boolean
}

export type RouteRequest = {
  origem_nome: string
  destino_nome: string
  calado_m: number
  margem_seguranca_m: number
  velocidade_embarcacao_kmh: number
  monitorar?: boolean
}

export type RouteSegment = {
  no_origem: number
  no_destino: number
  fid: number
  distancia_km: number
  profundidade_m: number | null
  transitavel: boolean
  tempo_h: number
}

export type GeoJsonFeature = {
  type: 'Feature'
  properties: Record<string, unknown>
  geometry: { type: string; coordinates: unknown }
}

export type GeoJsonFeatureCollection = {
  type: 'FeatureCollection'
  features: GeoJsonFeature[]
}

export type RouteResult = {
  rota_id: number | null
  origem: string
  destino: string
  distancia_total_km: number
  tempo_total_h: number
  custo_total: number
  trechos_criticos: number
  profundidade_minima_m: number | null
  geojson: GeoJsonFeatureCollection
  items: RouteSegment[]
}

export type SalvarRotaInput = {
  origem_nome: string
  destino_nome: string
  calado_m: number
  margem_seguranca_m: number
  velocidade_embarcacao_kmh: number
  distancia_total_km: number
  tempo_total_h: number
  custo_total: number
  trechos_criticos: number
  profundidade_minima_m: number | null
  geojson: GeoJsonFeatureCollection | null
  monitorar?: boolean
}

export type RotaSalva = {
  id: number
  usuario_id: number
  origem_nome: string
  destino_nome: string
  calado_m: number
  margem_seguranca_m: number
  velocidade_embarcacao_kmh: number
  distancia_total_km: number
  tempo_total_h: number
  custo_total: number
  trechos_criticos: number
  profundidade_minima_m: number | null
  rota_geojson: GeoJsonFeatureCollection | null
  monitorar: boolean
  created_at: string
}

export type ListaRotas = { items: RotaSalva[]; total: number }

export type AlteracaoRota = {
  id: number
  data_alteracao: string
  motivo: string
  variacao_nivel_cm: number | null
  estacao_origem: string | null
  distancia_total_km: number | null
  custo_total: number | null
  rota_geojson: GeoJsonFeatureCollection | null
}

export type ListaAlteracoes = { items: AlteracaoRota[] }

export type MonitorResultado = {
  rota_id: number
  monitorar: boolean
  estacao_referencia: string | null
  nivel_baseline_cm: number | null
  limiar_variacao_cm: number
  cooldown_min: number
}

export type EventoRota = {
  evento: string
  rota_id?: number
  motivo?: string
  variacao_nivel_cm?: number
  nova_distancia_km?: number
}

export type SnapshotGrafo = {
  gerado_em: string
  area: string
  total_nos: number
  total_arestas: number
  nos: [number, number, number][]
  arestas: [number, number, number, number, number | null][]
  estacoes: [string, number][]
}
