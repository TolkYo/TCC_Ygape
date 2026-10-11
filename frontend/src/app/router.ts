import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import { useSessionStore } from '@/stores/session'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { publica: true },
    },
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: { name: 'mapa' } },
        {
          path: 'mapa',
          name: 'mapa',
          component: () => import('@/views/MapaView.vue'),
          meta: { publica: true },
        },
        {
          path: 'rotas/nova',
          name: 'rota-nova',
          component: () => import('@/views/RotaNovaView.vue'),
          meta: { publica: true },
        },
        {
          path: 'historico',
          name: 'historico',
          component: () => import('@/views/HistoricoView.vue'),
        },
        {
          path: 'configuracoes',
          name: 'configuracoes',
          component: () => import('@/views/ConfiguracoesView.vue'),
          meta: { publica: true },
        },
        {
          path: 'admin/usuarios',
          name: 'admin-usuarios',
          component: () => import('@/views/admin/UsuariosView.vue'),
          meta: { requerAdmin: true },
        },
        {
          path: 'admin/coleta',
          name: 'admin-coleta',
          component: () => import('@/views/admin/ColetaView.vue'),
          meta: { requerAdmin: true },
        },
        {
          path: 'admin/logs',
          name: 'admin-logs',
          component: () => import('@/views/admin/LogsView.vue'),
          meta: { requerAdmin: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'nao-encontrado',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { publica: true },
    },
  ],
})

router.beforeEach((to) => {
  const session = useSessionStore()
  if (!to.meta.publica && !session.autenticado) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requerAdmin && !session.ehAdmin) {
    return { name: 'mapa' }
  }
  return true
})

export default router
