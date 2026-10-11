<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { api } from '@/services/endpoints'
import { ApiProblem } from '@/services/http'
import type { CriarUsuarioInput, Papel, UsuarioAdmin } from '@/types/api'
import { formatarDataHora } from '@/utils/formato'

const usuarios = ref<UsuarioAdmin[]>([])
const carregando = ref(false)
const erro = ref<string | null>(null)
const aviso = ref<string | null>(null)
const salvando = ref(false)

const novoServidor = reactive<CriarUsuarioInput>({
  nome: '',
  email: '',
  senha: '',
  papel: 'piloto',
})

function mensagem(e: unknown, padrao: string): string {
  return e instanceof ApiProblem ? e.message : padrao
}

async function carregar(): Promise<void> {
  carregando.value = true
  erro.value = null
  try {
    usuarios.value = (await api.listarUsuarios()).items
  } catch (e) {
    erro.value = mensagem(e, 'Falha ao carregar usuários.')
  } finally {
    carregando.value = false
  }
}

async function criar(): Promise<void> {
  salvando.value = true
  erro.value = null
  aviso.value = null
  try {
    await api.criarUsuario({ ...novoServidor })
    Object.assign(novoServidor, { nome: '', email: '', senha: '', papel: 'piloto' })
    await carregar()
    aviso.value = 'Usuário criado com sucesso.'
  } catch (e) {
    erro.value = mensagem(e, 'Falha ao criar usuário.')
  } finally {
    salvando.value = false
  }
}

async function alterarPapel(usuario: UsuarioAdmin, papel: Papel): Promise<void> {
  erro.value = null
  try {
    await api.atualizarUsuario(usuario.id, { papel })
    usuario.papel = papel
    aviso.value = `Papel de ${usuario.nome} atualizado.`
  } catch (e) {
    erro.value = mensagem(e, 'Falha ao atualizar usuário.')
  }
}

async function alternarAtivo(usuario: UsuarioAdmin): Promise<void> {
  erro.value = null
  try {
    if (usuario.ativo) {
      await api.desativarUsuario(usuario.id)
      usuario.ativo = false
      aviso.value = `${usuario.nome} desativado.`
    } else {
      await api.atualizarUsuario(usuario.id, { ativo: true })
      usuario.ativo = true
      aviso.value = `${usuario.nome} reativado.`
    }
  } catch (e) {
    erro.value = mensagem(e, 'Falha ao alterar status do usuário.')
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">Usuários</h1>
      <p class="text-sm text-ink-muted">Gestão de contas e perfis (administrador).</p>
    </header>

    <p v-if="erro" role="alert" class="rounded bg-danger/10 px-3 py-2 text-sm text-danger">
      {{ erro }}
    </p>
    <p v-if="aviso" role="status" class="rounded bg-success/10 px-3 py-2 text-sm text-success">
      {{ aviso }}
    </p>

    <form
      class="grid gap-4 rounded-lg border border-edge bg-surface-elevated p-4 sm:grid-cols-2 lg:grid-cols-4"
      @submit.prevent="criar"
    >
      <div>
        <label for="nome" class="mb-1 block text-sm font-medium">Nome</label>
        <input
          id="nome"
          v-model="novoServidor.nome"
          required
          minlength="2"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>
      <div>
        <label for="email" class="mb-1 block text-sm font-medium">E-mail</label>
        <input
          id="email"
          v-model="novoServidor.email"
          type="email"
          required
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>
      <div>
        <label for="senha" class="mb-1 block text-sm font-medium">Senha</label>
        <input
          id="senha"
          v-model="novoServidor.senha"
          type="password"
          required
          minlength="8"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        />
      </div>
      <div>
        <label for="papel" class="mb-1 block text-sm font-medium">Papel</label>
        <select
          id="papel"
          v-model="novoServidor.papel"
          class="w-full rounded border border-edge bg-surface px-3 py-2 text-sm focus:outline focus:outline-2 focus:outline-primary"
        >
          <option value="piloto">Piloto</option>
          <option value="admin">Administrador</option>
        </select>
      </div>
      <div class="sm:col-span-2 lg:col-span-4">
        <BaseButton tipo="submit" :desabilitado="salvando">
          {{ salvando ? 'Criando…' : 'Criar usuário' }}
        </BaseButton>
      </div>
    </form>

    <p v-if="carregando" class="text-sm text-ink-muted">Carregando usuários…</p>

    <div v-else class="overflow-x-auto rounded-lg border border-edge">
      <table class="w-full border-collapse text-sm">
        <thead class="bg-surface-muted text-left">
          <tr>
            <th class="px-3 py-2 font-medium">Nome</th>
            <th class="px-3 py-2 font-medium">E-mail</th>
            <th class="px-3 py-2 font-medium">Papel</th>
            <th class="px-3 py-2 font-medium">Status</th>
            <th class="px-3 py-2 font-medium">Criado em</th>
            <th class="px-3 py-2 font-medium">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="usuario in usuarios" :key="usuario.id" class="border-t border-edge">
            <td class="px-3 py-2">{{ usuario.nome }}</td>
            <td class="px-3 py-2 text-ink-muted">{{ usuario.email }}</td>
            <td class="px-3 py-2">
              <select
                :value="usuario.papel"
                class="rounded border border-edge bg-surface px-2 py-1 text-xs"
                @change="alterarPapel(usuario, ($event.target as HTMLSelectElement).value as Papel)"
              >
                <option value="piloto">Piloto</option>
                <option value="admin">Administrador</option>
              </select>
            </td>
            <td class="px-3 py-2">
              <StatusBadge
                :tom="usuario.ativo ? 'success' : 'unknown'"
                :label="usuario.ativo ? 'Ativo' : 'Inativo'"
              />
            </td>
            <td class="px-3 py-2 text-ink-muted">{{ formatarDataHora(usuario.criado_em) }}</td>
            <td class="px-3 py-2">
              <BaseButton
                :variante="usuario.ativo ? 'perigo' : 'secundaria'"
                @click="alternarAtivo(usuario)"
              >
                {{ usuario.ativo ? 'Desativar' : 'Reativar' }}
              </BaseButton>
            </td>
          </tr>
          <tr v-if="!usuarios.length">
            <td colspan="6" class="px-3 py-4 text-center text-ink-muted">
              Nenhum usuário encontrado.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
