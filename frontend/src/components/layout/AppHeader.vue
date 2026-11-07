<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'

defineProps<{ title: string; scanning: boolean }>()
const emit = defineEmits<{ 'toggle-sidebar': [] }>()
</script>

<template>
  <header class="z-30 flex h-14 shrink-0 items-center gap-3 bg-panel px-3 shadow-md sm:px-5">
    <button class="btn btn-ghost px-2 lg:hidden" title="Toggle navigation" @click="emit('toggle-sidebar')">
      <AppIcon name="menu" />
    </button>
    <RouterLink to="/" class="flex items-center gap-2.5">
      <span class="flex h-8 w-8 items-center justify-center rounded bg-accent text-white">
        <AppIcon name="camera" :size="18" />
      </span>
      <span class="text-lg font-semibold tracking-wide">{{ title }}</span>
    </RouterLink>
    <RouterLink
      to="/system"
      class="ml-auto flex items-center gap-2 rounded px-2 py-1 text-sm text-muted hover:bg-hover hover:text-fg"
      :title="scanning ? 'Library scan in progress' : 'System status'"
    >
      <span class="h-2 w-2 rounded-full" :class="scanning ? 'animate-pulse bg-warning' : 'bg-success'" />
      <span class="hidden sm:inline">{{ scanning ? 'Scanning' : 'Idle' }}</span>
    </RouterLink>
  </header>
</template>
