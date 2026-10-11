import { http } from './http'

import type {
  AtualizarUsuarioInput,
  ColetaInput,
  CriarUsuarioInput,
  GrafoStatus,
  ListaEstacoes,
  ListaLogs,
  ListaRotas,
  ListaUsuarios,
  LoginResult,
  PerfilUpdateInput,
  RotaSalva,
  RouteRequest,
  RouteResult,
  SalvarRotaInput,
  Usuario,
} from '@/types/api'

export const api = {
  login: (email: string, senha: string) => http.post<LoginResult>('/auth/login', { email, senha }),
  me: () => http.get<Usuario>('/auth/me'),
  atualizarPerfil: (payload: PerfilUpdateInput) => http.put<Usuario>('/auth/me', payload),
  listarUsuarios: () => http.get<ListaUsuarios>('/usuarios'),
  criarUsuario: (payload: CriarUsuarioInput) => http.post<Usuario>('/usuarios', payload),
  atualizarUsuario: (id: number, payload: AtualizarUsuarioInput) =>
    http.put<Usuario>(`/usuarios/${id}`, payload),
  desativarUsuario: (id: number) =>
    http.delete<{ id: number; ativo: boolean }>(`/usuarios/${id}`),
  listarEstacoes: () => http.get<ListaEstacoes>('/estacoes'),
  coletarNiveis: (payload: ColetaInput) => http.post<unknown>('/niveis/coletar', payload),
  grafoStatus: () => http.get<GrafoStatus>('/grafo/status'),
  listarLogs: (limite = 100) => http.get<ListaLogs>(`/logs?limite=${limite}`),
  calcularRota: (payload: RouteRequest) => http.post<RouteResult>('/rotas/calcular', payload),
  salvarRota: (payload: SalvarRotaInput) => http.post<RotaSalva>('/rotas', payload),
  listarRotas: () => http.get<ListaRotas>('/rotas'),
  obterRota: (id: number) => http.get<RotaSalva>(`/rotas/${id}`),
  removerRota: (id: number) => http.delete<{ id: number; removida: boolean }>(`/rotas/${id}`),
}
