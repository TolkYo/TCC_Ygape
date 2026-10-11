<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variante?: 'primaria' | 'secundaria' | 'perigo'
    tipo?: 'button' | 'submit' | 'reset'
    desabilitado?: boolean
  }>(),
  { variante: 'primaria', tipo: 'button', desabilitado: false },
)

const variantes = {
  primaria: 'bg-primary text-white hover:bg-primary-strong',
  secundaria: 'border border-edge bg-surface-elevated text-ink hover:bg-surface-muted',
  perigo: 'bg-danger text-white hover:brightness-95',
} as const

const classes = computed(() => variantes[props.variante])
</script>

<template>
  <button
    :type="tipo"
    :disabled="desabilitado"
    class="inline-flex items-center justify-center gap-2 rounded px-4 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-60"
    :class="classes"
  >
    <slot />
  </button>
</template>
