import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

type Tema = 'claro' | 'escuro'

const CHAVE_TEMA = 'ygape-tema'
const CHAVE_CONTRASTE = 'ygape-contraste'
const CHAVE_FONTE = 'ygape-fonte'
const ESCALAS_FONTE = [16, 18, 20]

export const useUiStore = defineStore('ui', () => {
  const tema = ref<Tema>((localStorage.getItem(CHAVE_TEMA) as Tema | null) ?? 'claro')
  const altoContraste = ref(localStorage.getItem(CHAVE_CONTRASTE) === 'true')
  const escalaFonte = ref(Number(localStorage.getItem(CHAVE_FONTE) ?? '0'))

  function aplicar(): void {
    const root = document.documentElement
    root.classList.toggle('dark', tema.value === 'escuro')
    root.classList.toggle('contrast-high', altoContraste.value)
    root.style.fontSize = `${ESCALAS_FONTE[escalaFonte.value] ?? ESCALAS_FONTE[0]}px`
  }

  function alternarTema(): void {
    tema.value = tema.value === 'claro' ? 'escuro' : 'claro'
  }

  function alternarContraste(): void {
    altoContraste.value = !altoContraste.value
  }

  function ciclarFonte(): void {
    escalaFonte.value = (escalaFonte.value + 1) % ESCALAS_FONTE.length
  }

  watch(
    [tema, altoContraste, escalaFonte],
    () => {
      localStorage.setItem(CHAVE_TEMA, tema.value)
      localStorage.setItem(CHAVE_CONTRASTE, String(altoContraste.value))
      localStorage.setItem(CHAVE_FONTE, String(escalaFonte.value))
      aplicar()
    },
    { immediate: true, flush: 'sync' },
  )

  return { tema, altoContraste, escalaFonte, aplicar, alternarTema, alternarContraste, ciclarFonte }
})
