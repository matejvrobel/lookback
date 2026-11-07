<script setup lang="ts">
defineProps<{ legend: string }>()
</script>

<template>
  <fieldset class="mb-8">
    <legend class="mb-3 w-full border-b border-line pb-2 text-lg font-light">{{ legend }}</legend>
    <slot />
  </fieldset>
</template>
