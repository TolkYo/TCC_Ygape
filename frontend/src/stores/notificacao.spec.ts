import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/endpoints', () => ({
  api: { listarRotas: vi.fn(), listarAlteracoes: vi.fn() },
}))

import { api } from '@/services/endpoints'
import { setToken } from '@/services/http'

import { useNotificacaoStore } from './notificacao'

const apiMock = vi.mocked(api)

class FakeWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: FakeWebSocket[] = []
  url: string
  readyState = 0
  onopen: (() => void) | null = null
  onmessage: ((evento: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  abrir(): void {
    this.readyState = 1
    this.onopen?.()
  }

  receber(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }

  close(): void {
    this.readyState = 3
    this.onclose?.()
  }
}

describe('store de notificações', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket as unknown as typeof WebSocket)
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('conecta e transforma eventos do WS em avisos', () => {
    setToken('token-1')
    const store = useNotificacaoStore()

    store.conectar()
    const ws = FakeWebSocket.instances.at(-1)
    expect(ws).toBeDefined()
    ws?.abrir()
    expect(store.conectado).toBe(true)

    ws?.receber({ evento: 'rota_alterada', rota_id: 5, motivo: 'variacao_nivel', variacao_nivel_cm: 40, nova_distancia_km: 200 })

    expect(store.avisos).toHaveLength(1)
    expect(store.avisos[0]?.texto).toContain('Rota 5')
    expect(store.avisos[0]?.rota_id).toBe(5)
  })

  it('não conecta sem token', () => {
    const store = useNotificacaoStore()
    store.conectar()
    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('marca desconectado e agenda reconexão ao fechar', () => {
    vi.useFakeTimers()
    setToken('token-1')
    const store = useNotificacaoStore()
    store.conectar()
    const ws = FakeWebSocket.instances.at(-1)
    ws?.abrir()
    expect(store.conectado).toBe(true)

    ws?.close()
    expect(store.conectado).toBe(false)

    vi.advanceTimersByTime(2000)
    expect(FakeWebSocket.instances.length).toBeGreaterThan(1)
  })

  it('fallback: detecta alterações novas sem duplicar', async () => {
    apiMock.listarRotas.mockResolvedValue({
      items: [{ id: 7, monitorar: true } as never],
      total: 1,
    })
    apiMock.listarAlteracoes.mockResolvedValue({
      items: [{ id: 100, motivo: 'variacao_nivel', variacao_nivel_cm: 35, distancia_total_km: 210 } as never],
    })
    const store = useNotificacaoStore()

    await store.checarAlteracoes(true)
    expect(store.avisos).toHaveLength(1)

    await store.checarAlteracoes(true)
    expect(store.avisos).toHaveLength(1)
  })
})
