<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="mx-auto max-w-md py-16 text-center">
    <p class="text-5xl font-semibold text-primary">404</p>
    <h1 class="mt-2 text-xl font-semibold">Página não encontrada</h1>
    <p class="mt-1 text-sm text-ink-muted">O endereço acessado não existe.</p>
    <RouterLink
      :to="{ name: 'mapa' }"
      class="mt-6 inline-block rounded bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-strong"
    >
      Voltar ao mapa
    </RouterLink>
  </section>
</template>
