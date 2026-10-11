<script setup lang="ts">
import type { FeatureCollection } from 'geojson'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { Estacao, RouteResult } from '@/types/api'

const props = withDefaults(
  defineProps<{
    estacoes?: Estacao[]
    rota?: RouteResult | null
    altura?: string
  }>(),
  { estacoes: () => [], rota: null, altura: '70vh' },
)

const emit = defineEmits<{ selecionarEstacao: [Estacao] }>()

const COR_OK = '#1a7f4b'
const COR_ALERTA = '#b7791f'
const COR_DESCONHECIDO = '#6b7280'

const container = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
let estacoesLayer: L.LayerGroup | null = null
let rotaLayer: L.GeoJSON | null = null

function corEstacao(estacao: Estacao): string {
  if (estacao.nivel_atual_cm === null) {
    return COR_DESCONHECIDO
  }
  if (estacao.cota_minima_historica_m === null) {
    return COR_OK
  }
  const nivelMetros = estacao.nivel_atual_cm / 100
  return nivelMetros <= estacao.cota_minima_historica_m + 0.5 ? COR_ALERTA : COR_OK
}

function criarPopup(estacao: Estacao): HTMLElement {
  const div = document.createElement('div')
  const titulo = document.createElement('strong')
  titulo.textContent = estacao.nome_estacao
  div.appendChild(titulo)

  const linhas = [
    estacao.nome_rio ? `Rio: ${estacao.nome_rio}` : null,
    estacao.municipio ? `Município: ${estacao.municipio}` : null,
    estacao.nivel_atual_cm !== null
      ? `Nível atual: ${estacao.nivel_atual_cm} cm`
      : 'Nível atual: indisponível',
    estacao.atualizado_em ? `Atualizado: ${estacao.atualizado_em}` : null,
  ].filter((linha): linha is string => Boolean(linha))

  for (const texto of linhas) {
    const p = document.createElement('div')
    p.textContent = texto
    div.appendChild(p)
  }
  return div
}

function renderizarEstacoes(): void {
  if (!map) return
  if (estacoesLayer) {
    estacoesLayer.clearLayers()
  } else {
    estacoesLayer = L.layerGroup().addTo(map)
  }

  for (const estacao of props.estacoes) {
    const marker = L.circleMarker([estacao.latitude, estacao.longitude], {
      radius: 6,
      color: '#ffffff',
      weight: 1.5,
      fillColor: corEstacao(estacao),
      fillOpacity: 1,
    })
    marker.bindPopup(criarPopup(estacao))
    marker.on('click', () => emit('selecionarEstacao', estacao))
    estacoesLayer.addLayer(marker)
  }
}

function renderizarRota(): void {
  if (!map) return
  if (rotaLayer) {
    map.removeLayer(rotaLayer)
    rotaLayer = null
  }
  if (!props.rota || props.rota.geojson.features.length === 0) {
    return
  }

  rotaLayer = L.geoJSON(props.rota.geojson as unknown as FeatureCollection, {
    style: { color: '#0b6bcb', weight: 4, opacity: 0.9 },
  }).addTo(map)

  const bounds = rotaLayer.getBounds()
  if (bounds.isValid()) {
    map.fitBounds(bounds, { padding: [30, 30] })
  }
}

onMounted(() => {
  if (!container.value) return
  map = L.map(container.value, { center: [-3.5, -60], zoom: 6 })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; colaboradores do OpenStreetMap',
    maxZoom: 19,
  }).addTo(map)

  renderizarEstacoes()
  renderizarRota()
  window.setTimeout(() => map?.invalidateSize(), 0)
})

watch(
  () => props.estacoes,
  () => renderizarEstacoes(),
)
watch(
  () => props.rota,
  () => renderizarRota(),
)

onBeforeUnmount(() => {
  map?.remove()
  map = null
  estacoesLayer = null
  rotaLayer = null
})

defineExpose({
  fitRota(): void {
    if (map && rotaLayer) {
      const bounds = rotaLayer.getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [30, 30] })
      }
    }
  },
})
</script>

<template>
  <div
    ref="container"
    class="z-0 w-full overflow-hidden rounded-lg border border-edge bg-surface-muted"
    :style="{ height: altura }"
    role="region"
    aria-label="Mapa de hidrovias e estações"
  />
</template>
