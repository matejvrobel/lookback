<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterView } from 'vue-router'
import { api } from './api/client'
import type { SystemStatus } from './api/types'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import { useSettingsStore } from './stores/settings'

const settingsStore = useSettingsStore()
const sidebarOpen = ref(false)
const scanning = ref(false)
const darkQuery = window.matchMedia('(prefers-color-scheme: dark)')
let statusTimer: number | undefined

const theme = computed(() => settingsStore.settings?.ui.theme ?? 'dark')
const instanceName = computed(() => settingsStore.settings?.general.instance_name || 'RecordViewer')

function applyTheme() {
  const dark = theme.value === 'dark' || (theme.value === 'system' && darkQuery.matches)
  document.documentElement.classList.toggle('dark', dark)
}

async function pollStatus() {
  try {
    scanning.value = (await api<SystemStatus>('/system/status')).scanner.running
  } catch {
    scanning.value = false
  }
}

watch(theme, applyTheme, { immediate: true })

onMounted(() => {
  settingsStore.load().catch(() => undefined)
  darkQuery.addEventListener('change', applyTheme)
  pollStatus()
  statusTimer = window.setInterval(pollStatus, 15000)
})

onBeforeUnmount(() => {
  darkQuery.removeEventListener('change', applyTheme)
  window.clearInterval(statusTimer)
})
</script>

<template>
  <div class="flex h-full flex-col">
    <AppHeader :title="instanceName" :scanning="scanning" @toggle-sidebar="sidebarOpen = !sidebarOpen" />
    <div class="flex min-h-0 flex-1">
      <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
      <main class="min-w-0 flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>
  </div>
</template>
