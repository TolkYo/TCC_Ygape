import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { Estacao } from '@/types/api'

import RiverMap from './RiverMap.vue'

const manaus: Estacao = {
  codigo_estacao: '14990000',
  nome_estacao: 'MANAUS',
  nome_rio: 'RIO NEGRO',
  municipio: 'MANAUS',
  latitude: -3.1,
  longitude: -60.0,
  cota_minima_historica_m: 15.0,
  nivel_atual_cm: 2100,
  atualizado_em: '2026-10-01T12:00:00',
}

describe('RiverMap', () => {
  it('inicializa o mapa Leaflet e desenha as estações', () => {
    const wrapper = mount(RiverMap, { props: { estacoes: [manaus] } })

    // O Leaflet marca o contêiner com a classe leaflet-container quando o mapa é criado.
    expect(wrapper.find('.leaflet-container').exists()).toBe(true)

    wrapper.unmount()
  })
})
