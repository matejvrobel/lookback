<script setup lang="ts">
const model = defineModel<boolean>({ required: true })
defineProps<{ label?: string }>()
</script>

<template>
  <label class="inline-flex cursor-pointer items-center gap-3 select-none">
    <button
      type="button"
      role="switch"
      :aria-checked="model"
      class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors"
      :class="model ? 'bg-accent' : 'bg-line'"
      @click="model = !model"
    >
      <span
        class="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform"
        :class="model ? 'translate-x-6' : 'translate-x-1'"
      />
    </button>
    <span v-if="label" class="text-sm">{{ label }}</span>
  </label>
</template>
