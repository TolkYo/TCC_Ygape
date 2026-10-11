export function formatarNumero(valor: number | null | undefined, digitos = 1): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) {
    return '—'
  }
  return valor.toLocaleString('pt-BR', {
    minimumFractionDigits: digitos,
    maximumFractionDigits: digitos,
  })
}

export function formatarInteiro(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) {
    return '—'
  }
  return valor.toLocaleString('pt-BR')
}

export function formatarDataHora(valor: string | null | undefined): string {
  if (!valor) {
    return '—'
  }
  const data = new Date(valor.includes('T') ? valor : `${valor.replace(' ', 'T')}Z`)
  if (Number.isNaN(data.getTime())) {
    return valor
  }
  return data.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
