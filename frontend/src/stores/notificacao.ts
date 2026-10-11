import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/services/endpoints'
import { apiBaseUrl, getToken } from '@/services/http'
import type { EventoRota } from '@/types/api'

export type Aviso = {
  id: number
  texto: string
  tipo: 'info' | 'warning'
  rota_id?: number
}

const INTERVALO_POLL_MS = 5 * 60 * 1000

function urlWebSocket(token: string): string {
  let base = apiBaseUrl
  if (base.startsWith('http')) {
    base = base.replace(/^http/, 'ws')
  } else {
    const protocolo = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
    base = `${protocolo}${window.location.host}${base}`
  }
  return `${base}/ws?token=${encodeURIComponent(token)}`
}

export const useNotificacaoStore = defineStore('notificacao', () => {
  const conectado = ref(false)
  const avisos = ref<Aviso[]>([])

  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null
  let pollTimer: number | null = null
  let tentativas = 0
  let sequencia = 0
  const vistos = new Set<number>()

  function registar(evento: EventoRota): void {
    sequencia += 1
    const texto =
      evento.evento === 'rota_alterada'
        ? `Rota ${evento.rota_id}: traçado alterado (${evento.motivo ?? 'variação'}, ` +
          `${evento.variacao_nivel_cm ?? '?'} cm; nova distância ${evento.nova_distancia_km ?? '?'} km).`
        : `Evento: ${evento.evento}`
    avisos.value = [...avisos.value, { id: sequencia, texto, tipo: 'warning', rota_id: evento.rota_id }]
  }

  function limparAviso(id: number): void {
    avisos.value = avisos.value.filter((aviso) => aviso.id !== id)
  }

  // Fallback (RN027): quando o WS está indisponível, verifica alterações a cada 5 min.
  async function checarAlteracoes(notificar: boolean): Promise<void> {
    try {
      const rotas = (await api.listarRotas()).items.filter((item) => item.monitorar)
      for (const rota of rotas) {
        const items = (await api.listarAlteracoes(rota.id)).items
        for (const alteracao of items) {
          if (vistos.has(alteracao.id)) continue
          vistos.add(alteracao.id)
          if (notificar) {
            registar({
              evento: 'rota_alterada',
              rota_id: rota.id,
              motivo: alteracao.motivo,
              variacao_nivel_cm: alteracao.variacao_nivel_cm ?? undefined,
              nova_distancia_km: alteracao.distancia_total_km ?? undefined,
            })
          }
        }
      }
    } catch {
      // offline ou sem sessão — tenta no próximo ciclo
    }
  }

  function iniciarFallback(): void {
    if (pollTimer !== null) return
    pollTimer = window.setInterval(() => void checarAlteracoes(true), INTERVALO_POLL_MS)
  }

  function pararFallback(): void {
    if (pollTimer !== null) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function agendarReconexao(): void {
    if (reconnectTimer !== null) return
    tentativas += 1
    const espera = Math.min(30000, 1000 * 2 ** Math.min(tentativas, 5))
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      conectar()
    }, espera)
  }

  function conectar(): void {
    const token = getToken()
    if (!token) return
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
    try {
      ws = new WebSocket(urlWebSocket(token))
    } catch {
      agendarReconexao()
      return
    }
    ws.onopen = () => {
      conectado.value = true
      tentativas = 0
      pararFallback()
    }
    ws.onmessage = (evento) => {
      try {
        registar(JSON.parse(evento.data) as EventoRota)
      } catch {
        // mensagem inválida — ignora
      }
    }
    ws.onclose = () => {
      conectado.value = false
      ws = null
      iniciarFallback()
      agendarReconexao()
    }
    ws.onerror = () => {
      ws?.close()
    }
  }

  function desconectar(): void {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    pararFallback()
    ws?.close()
    ws = null
    conectado.value = false
  }

  return { conectado, avisos, conectar, desconectar, limparAviso, checarAlteracoes }
})
