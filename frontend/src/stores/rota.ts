import { defineStore } from 'pinia'
import { ref } from 'vue'

import { guardarRotas, lerRotas as lerRotasCache, lerSnapshot } from '@/services/cache'
import { api } from '@/services/endpoints'
import { ApiProblem } from '@/services/http'
import { calcularOffline } from '@/services/roteador'
import { useEstacoesStore } from '@/stores/estacoes'
import { useOfflineStore } from '@/stores/offline'
import type { AlteracaoRota, MonitorResultado, RotaSalva, RouteRequest, RouteResult, SalvarRotaInput } from '@/types/api'

function mensagemErro(erro: unknown, padrao: string): string {
  return erro instanceof ApiProblem ? erro.message : padrao
}

export const useRotaStore = defineStore('rota', () => {
  const parametros = ref<RouteRequest>({
    origem_nome: '',
    destino_nome: '',
    calado_m: 2,
    margem_seguranca_m: 0.5,
    velocidade_embarcacao_kmh: 12,
  })
  const resultado = ref<RouteResult | null>(null)
  const calculando = ref(false)
  const erro = ref<string | null>(null)
  const idSalvo = ref<number | null>(null)
  const salvoLocal = ref(false)
  const calculadoOffline = ref(false)

  const historico = ref<RotaSalva[]>([])
  const carregandoHistorico = ref(false)
  const salvando = ref(false)
  const erroHistorico = ref<string | null>(null)
  const historicoDoCache = ref(false)

  function montarPayload(r: RouteResult): SalvarRotaInput {
    return {
      origem_nome: parametros.value.origem_nome,
      destino_nome: parametros.value.destino_nome,
      calado_m: parametros.value.calado_m,
      margem_seguranca_m: parametros.value.margem_seguranca_m,
      velocidade_embarcacao_kmh: parametros.value.velocidade_embarcacao_kmh,
      distancia_total_km: r.distancia_total_km,
      tempo_total_h: r.tempo_total_h,
      custo_total: r.custo_total,
      trechos_criticos: r.trechos_criticos,
      profundidade_minima_m: r.profundidade_minima_m,
      geojson: r.geojson,
      monitorar: parametros.value.monitorar ?? false,
    }
  }

  async function calcularOfflineSePossivel(): Promise<RouteResult | null> {
    const snap = await lerSnapshot()
    if (!snap) return null
    const est = useEstacoesStore()
    const codigoDe = (nome: string) => est.itens.find((e) => e.nome_estacao === nome)?.codigo_estacao
    const origem = codigoDe(parametros.value.origem_nome)
    const destino = codigoDe(parametros.value.destino_nome)
    if (!origem || !destino) return null
    return calcularOffline(
      snap.dados,
      origem,
      destino,
      parametros.value.calado_m,
      parametros.value.margem_seguranca_m,
      parametros.value.velocidade_embarcacao_kmh,
    )
  }

  async function calcular(): Promise<void> {
    calculando.value = true
    erro.value = null
    idSalvo.value = null
    salvoLocal.value = false
    calculadoOffline.value = false
    try {
      resultado.value = await api.calcularRota({ ...parametros.value })
    } catch (e) {
      resultado.value = null
      if (!(e instanceof ApiProblem)) {
        const offline = await calcularOfflineSePossivel()
        if (offline) {
          resultado.value = offline
          calculadoOffline.value = true
          return
        }
      }
      erro.value = mensagemErro(e, 'Falha ao calcular a rota.')
    } finally {
      calculando.value = false
    }
  }

  async function salvar(): Promise<RotaSalva | null> {
    if (!resultado.value) {
      return null
    }
    salvando.value = true
    erro.value = null
    const payload = montarPayload(resultado.value)
    try {
      const salva = await api.salvarRota(payload)
      idSalvo.value = salva.id
      salvoLocal.value = false
      historico.value = [salva, ...historico.value.filter((item) => item.id !== salva.id)]
      return salva
    } catch (e) {
      if (e instanceof ApiProblem) {
        erro.value = e.message
        return null
      }
      await useOfflineStore().enfileirar(payload)
      salvoLocal.value = true
      return null
    } finally {
      salvando.value = false
    }
  }

  async function carregarHistorico(): Promise<void> {
    carregandoHistorico.value = true
    erroHistorico.value = null
    try {
      historico.value = (await api.listarRotas()).items
      historicoDoCache.value = false
      void guardarRotas(historico.value).catch(() => undefined)
    } catch (e) {
      const cache = await lerRotasCache()
      if (cache.length) {
        historico.value = cache
        historicoDoCache.value = true
      } else {
        erroHistorico.value = mensagemErro(e, 'Falha ao carregar o histórico.')
      }
    } finally {
      carregandoHistorico.value = false
    }
  }

  async function remover(id: number): Promise<boolean> {
    try {
      await api.removerRota(id)
      historico.value = historico.value.filter((item) => item.id !== id)
      return true
    } catch (e) {
      erroHistorico.value = mensagemErro(e, 'Falha ao remover a rota.')
      return false
    }
  }

  async function monitorar(id: number, valor: boolean): Promise<MonitorResultado | null> {
    try {
      const resultado = await api.monitorarRota(id, valor)
      const item = historico.value.find((rota) => rota.id === id)
      if (item) {
        item.monitorar = valor
      }
      return resultado
    } catch (e) {
      erroHistorico.value = mensagemErro(e, 'Falha ao atualizar o monitoramento.')
      return null
    }
  }

  async function alteracoes(id: number): Promise<AlteracaoRota[]> {
    try {
      return (await api.listarAlteracoes(id)).items
    } catch (e) {
      erroHistorico.value = mensagemErro(e, 'Falha ao carregar as alterações da rota.')
      return []
    }
  }

  function inverter(): void {
    parametros.value = {
      ...parametros.value,
      origem_nome: parametros.value.destino_nome,
      destino_nome: parametros.value.origem_nome,
    }
    resultado.value = null
    idSalvo.value = null
    salvoLocal.value = false
    calculadoOffline.value = false
  }

  function limpar(): void {
    resultado.value = null
    erro.value = null
    idSalvo.value = null
    salvoLocal.value = false
    calculadoOffline.value = false
  }

  return {
    parametros,
    resultado,
    calculando,
    erro,
    idSalvo,
    salvoLocal,
    calculadoOffline,
    historico,
    carregandoHistorico,
    salvando,
    erroHistorico,
    historicoDoCache,
    calcular,
    salvar,
    carregarHistorico,
    remover,
    monitorar,
    alteracoes,
    inverter,
    limpar,
  }
})
