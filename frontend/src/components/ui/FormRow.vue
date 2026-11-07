<script setup lang="ts">
defineProps<{ label: string; help?: string; inputId?: string }>()
</script>

<template>
  <div class="flex flex-col gap-1.5 py-2.5 sm:flex-row sm:gap-6">
    <label :for="inputId" class="shrink-0 text-sm font-medium sm:w-52 sm:pt-1.5 sm:text-right">{{ label }}</label>
    <div class="min-w-0 max-w-xl flex-1">
      <slot />
      <p v-if="help" class="mt-1 text-xs text-muted">{{ help }}</p>
    </div>
  </div>
</template>
