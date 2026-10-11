import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/services/endpoints'
import { ApiProblem, getToken, setToken } from '@/services/http'
import type { PerfilUpdateInput, Usuario } from '@/types/api'

const USUARIO_KEY = 'hidrowize-usuario'

function lerUsuarioCache(): Usuario | null {
  const cru = localStorage.getItem(USUARIO_KEY)
  if (!cru) {
    return null
  }
  try {
    return JSON.parse(cru) as Usuario
  } catch {
    return null
  }
}

function guardarUsuarioCache(usuario: Usuario | null): void {
  if (usuario) {
    localStorage.setItem(USUARIO_KEY, JSON.stringify(usuario))
  } else {
    localStorage.removeItem(USUARIO_KEY)
  }
}

export const useSessionStore = defineStore('session', () => {
  const usuario = ref<Usuario | null>(null)
  const carregando = ref(false)

  const autenticado = computed(() => usuario.value !== null)
  const ehAdmin = computed(() => usuario.value?.papel === 'admin')

  async function login(email: string, senha: string): Promise<Usuario> {
    carregando.value = true
    try {
      const resultado = await api.login(email, senha)
      setToken(resultado.access_token)
      usuario.value = resultado.usuario
      guardarUsuarioCache(resultado.usuario)
      return resultado.usuario
    } finally {
      carregando.value = false
    }
  }

  async function restaurar(): Promise<void> {
    if (!getToken()) {
      return
    }
    try {
      usuario.value = await api.me()
      guardarUsuarioCache(usuario.value)
    } catch (e) {
      if (e instanceof ApiProblem && (e.status === 401 || e.status === 403)) {
        setToken(null)
        usuario.value = null
        guardarUsuarioCache(null)
      } else {
        // Sem rede: mantém a sessão a partir do cache local.
        usuario.value = lerUsuarioCache()
      }
    }
  }

  function logout(): void {
    setToken(null)
    usuario.value = null
    guardarUsuarioCache(null)
  }

  async function atualizarPerfil(input: PerfilUpdateInput): Promise<Usuario> {
    const atualizado = await api.atualizarPerfil(input)
    usuario.value = atualizado
    guardarUsuarioCache(atualizado)
    return atualizado
  }

  return {
    usuario,
    carregando,
    autenticado,
    ehAdmin,
    login,
    restaurar,
    logout,
    atualizarPerfil,
  }
})
