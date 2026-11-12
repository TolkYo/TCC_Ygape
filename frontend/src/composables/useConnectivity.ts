import { onMounted, onUnmounted, ref } from 'vue'

// @id FUN-TS-UI-008 | @categoria UI | @catalogo FUNCOES.md
export function useConnectivity() {
  const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
  const ultimaMudanca = ref<Date | null>(null)

  // @id FUN-TS-UI-009 | @categoria UI | @catalogo FUNCOES.md
  function atualizar(): void {
    online.value = navigator.onLine
    ultimaMudanca.value = new Date()
  }

  onMounted(() => {
    window.addEventListener('online', atualizar)
    window.addEventListener('offline', atualizar)
  })

  onUnmounted(() => {
    window.removeEventListener('online', atualizar)
    window.removeEventListener('offline', atualizar)
  })

  return { online, ultimaMudanca, atualizar }
}
