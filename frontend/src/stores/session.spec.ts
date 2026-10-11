import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/endpoints', () => ({
  api: { login: vi.fn(), me: vi.fn(), atualizarPerfil: vi.fn() },
}))

import { api } from '@/services/endpoints'
import { ApiProblem, getToken, setToken } from '@/services/http'
import type { Usuario } from '@/types/api'

import { useSessionStore } from './session'

const apiMock = vi.mocked(api)

const USUARIO: Usuario = { id: 2, nome: 'Administrador', email: 'admin@ygape.local', papel: 'admin' }

describe('store de sessão', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('faz login, guarda o token e o usuário em cache', async () => {
    apiMock.login.mockResolvedValue({
      access_token: 'token-1',
      token_type: 'bearer',
      expires_in: 100,
      usuario: USUARIO,
    })
    const store = useSessionStore()

    await store.login('admin@ygape.local', 'segredo123')

    expect(store.autenticado).toBe(true)
    expect(store.ehAdmin).toBe(true)
    expect(getToken()).toBe('token-1')
    expect(localStorage.getItem('hidrowize-usuario')).toContain('admin@ygape.local')
  })

  it('mantém a sessão pelo cache quando a API está inacessível', async () => {
    setToken('token-1')
    localStorage.setItem('hidrowize-usuario', JSON.stringify(USUARIO))
    apiMock.me.mockRejectedValue(new TypeError('falha de rede'))
    const store = useSessionStore()

    await store.restaurar()

    expect(store.usuario).toEqual(USUARIO)
    expect(getToken()).toBe('token-1')
  })

  it('descarta a sessão quando o token é rejeitado (401)', async () => {
    setToken('token-invalido')
    apiMock.me.mockRejectedValue(new ApiProblem('invalid_token', 'expirado', 401))
    const store = useSessionStore()

    await store.restaurar()

    expect(store.usuario).toBeNull()
    expect(getToken()).toBeNull()
  })

  it('atualiza o perfil do usuário', async () => {
    apiMock.atualizarPerfil.mockResolvedValue({ ...USUARIO, nome: 'Novo Nome' })
    const store = useSessionStore()

    const atualizado = await store.atualizarPerfil({ nome: 'Novo Nome' })

    expect(atualizado.nome).toBe('Novo Nome')
    expect(store.usuario?.nome).toBe('Novo Nome')
    expect(localStorage.getItem('hidrowize-usuario')).toContain('Novo Nome')
  })
})
