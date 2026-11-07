<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import AppIcon from './AppIcon.vue'

withDefaults(defineProps<{ title: string; width?: string }>(), { width: 'max-w-2xl' })
const emit = defineEmits<{ close: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 sm:pt-20" @mousedown.self="emit('close')">
      <div class="w-full rounded-md bg-panel shadow-2xl" :class="width" role="dialog" aria-modal="true">
        <header class="flex items-center justify-between border-b border-line px-5 py-3">
          <h2 class="text-lg font-medium">{{ title }}</h2>
          <button class="btn btn-ghost px-2" title="Close" @click="emit('close')"><AppIcon name="x" /></button>
        </header>
        <div class="max-h-[70vh] overflow-y-auto px-5 py-4">
          <slot />
        </div>
        <footer class="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>
