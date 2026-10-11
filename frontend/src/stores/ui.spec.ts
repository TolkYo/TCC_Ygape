import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useUiStore } from './ui'

describe('store de configurações de interface', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    document.documentElement.className = ''
    document.documentElement.style.fontSize = ''
  })

  it('alterna o tema aplicando a classe dark no <html>', () => {
    const ui = useUiStore()

    expect(document.documentElement.classList.contains('dark')).toBe(false)
    ui.alternarTema()
    expect(ui.tema).toBe('escuro')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('ygape-tema')).toBe('escuro')

    ui.alternarTema()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('alterna o alto contraste', () => {
    const ui = useUiStore()

    ui.alternarContraste()
    expect(ui.altoContraste).toBe(true)
    expect(document.documentElement.classList.contains('contrast-high')).toBe(true)
    expect(localStorage.getItem('ygape-contraste')).toBe('true')
  })

  it('cicla o tamanho da fonte entre três escalas', () => {
    const ui = useUiStore()

    expect(document.documentElement.style.fontSize).toBe('16px')
    ui.ciclarFonte()
    expect(ui.escalaFonte).toBe(1)
    expect(document.documentElement.style.fontSize).toBe('18px')
    ui.ciclarFonte()
    ui.ciclarFonte()
    expect(ui.escalaFonte).toBe(0)
    expect(document.documentElement.style.fontSize).toBe('16px')
  })
})
