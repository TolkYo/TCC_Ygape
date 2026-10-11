import { describe, expect, it } from 'vitest'

import { formatarInteiro, formatarNumero } from './formato'

describe('utilitários de formatação', () => {
  it('formata números com casas decimais no padrão pt-BR', () => {
    expect(formatarNumero(1234.5)).toBe('1.234,5')
    expect(formatarNumero(0.519, 2)).toBe('0,52')
  })

  it('retorna travessão para valores ausentes', () => {
    expect(formatarNumero(null)).toBe('—')
    expect(formatarNumero(undefined)).toBe('—')
    expect(formatarNumero(Number.NaN)).toBe('—')
    expect(formatarInteiro(null)).toBe('—')
  })

  it('formata inteiros com separador de milhar', () => {
    expect(formatarInteiro(121661)).toBe('121.661')
  })
})
