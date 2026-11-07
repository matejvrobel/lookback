<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, errorMessage } from '../../api/client'
import type { Camera } from '../../api/types'
import CameraEditModal from '../../components/settings/CameraEditModal.vue'
import AppIcon from '../../components/ui/AppIcon.vue'
import PageToolbar from '../../components/ui/PageToolbar.vue'
import { useCatalogStore } from '../../stores/catalog'

const catalog = useCatalogStore()
const editing = ref<Camera | null>(null)
const modalOpen = ref(false)
const notice = ref<string | null>(null)

const MATCH_LABELS = { folder: 'Folder', prefix: 'Prefix', regex: 'Regex' } as const

function openEditor(camera: Camera | null) {
  editing.value = camera
  modalOpen.value = true
}

async function closeEditor() {
  modalOpen.value = false
  window.setTimeout(() => catalog.load(true), 1500)
}

async function rematch() {
  try {
    const result = await api<{ changed: number }>('/system/rematch', { method: 'POST' })
    notice.value = `Rematch finished: ${result.changed} recording(s) reassigned.`
    await catalog.load(true)
  } catch (exc) {
    notice.value = errorMessage(exc)
  }
}

onMounted(() => catalog.load(true))
</script>

<template>
  <PageToolbar>
    <button class="btn btn-ghost" @click="openEditor(null)">
      <AppIcon name="plus" />
      Add Camera
    </button>
    <button class="btn btn-ghost" title="Re-run camera matching for all indexed files" @click="rematch">
      <AppIcon name="refresh" />
      Rematch Files
    </button>
    <template #right>
      <span v-if="notice" class="text-sm text-muted">{{ notice }}</span>
    </template>
  </PageToolbar>

  <div class="p-4 sm:p-6">
    <div v-if="catalog.loaded && !catalog.cameras.length" class="card text-center">
      <AppIcon name="camera" :size="40" class="mx-auto mb-3 text-muted" />
      <p class="mb-1 text-lg">No cameras defined yet</p>
      <p class="mb-4 text-sm text-muted">Recordings are still indexed and shown as "Unassigned" until a camera claims them.</p>
      <button class="btn btn-primary" @click="openEditor(null)">Add your first camera</button>
    </div>

    <div v-else class="overflow-x-auto rounded-md bg-panel shadow-sm">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-line text-xs tracking-wide text-muted uppercase">
          <tr>
            <th class="px-4 py-3">Name</th>
            <th class="px-4 py-3">Match</th>
            <th class="px-4 py-3">Expression</th>
            <th class="px-4 py-3 text-right">Priority</th>
            <th class="px-4 py-3 text-right">Recordings</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="camera in catalog.cameras"
            :key="camera.id"
            class="cursor-pointer border-b border-line last:border-0 hover:bg-hover"
            :class="{ 'opacity-50': !camera.enabled }"
            @click="openEditor(camera)"
          >
            <td class="px-4 py-3">
              <span class="flex items-center gap-2.5">
                <span class="h-3 w-3 rounded-full" :style="{ background: camera.color }" />
                {{ camera.name }}
              </span>
            </td>
            <td class="px-4 py-3"><span class="badge bg-raised">{{ MATCH_LABELS[camera.match_type] }}</span></td>
            <td class="max-w-xs truncate px-4 py-3 font-mono text-xs text-muted">{{ camera.match_value }}</td>
            <td class="px-4 py-3 text-right tabular-nums">{{ camera.priority }}</td>
            <td class="px-4 py-3 text-right tabular-nums">{{ camera.recording_count.toLocaleString() }}</td>
            <td class="px-4 py-3 text-right text-muted"><AppIcon name="edit" :size="16" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <CameraEditModal v-if="modalOpen" :camera="editing" @close="closeEditor" />
</template>
