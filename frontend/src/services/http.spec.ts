import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiProblem, getToken, http, setToken } from './http'

function resposta(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as unknown as Response
}

describe('cliente HTTP', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('guarda, recupera e limpa o token', () => {
    expect(getToken()).toBeNull()
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('desempacota o envelope de sucesso', async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ success: true, data: { ok: 1 } }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(http.get<{ ok: number }>('/teste')).resolves.toEqual({ ok: 1 })
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('lança ApiProblem quando o backend retorna erro', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          resposta({ success: false, error: { code: 'x', message: 'falhou' } }, false, 400),
        ),
    )

    await expect(http.get('/teste')).rejects.toBeInstanceOf(ApiProblem)
  })

  it('anexa o token de sessão quando presente', async () => {
    setToken('token-123')
    const fetchMock = vi.fn().mockResolvedValue(resposta({ success: true, data: null }))
    vi.stubGlobal('fetch', fetchMock)

    await http.get('/teste')

    const call = fetchMock.mock.calls[0]
    expect(call).toBeDefined()
    const init = call![1] as RequestInit
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer token-123')
  })
})
