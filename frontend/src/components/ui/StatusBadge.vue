<script setup lang="ts">
import { computed } from 'vue'

type Tom = 'success' | 'warning' | 'danger' | 'info' | 'unknown'

const props = defineProps<{ tom?: Tom; label: string }>()

const paleta: Record<Tom, string> = {
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  danger: 'bg-danger/10 text-danger',
  info: 'bg-info/10 text-info',
  unknown: 'bg-unknown/10 text-unknown',
}

const classes = computed(() => paleta[props.tom ?? 'unknown'])
</script>

<template>
  <span
    class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
    :class="classes"
  >
    {{ label }}
  </span>
</template>
