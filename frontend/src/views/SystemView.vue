<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api, errorMessage } from '../api/client'
import type { SystemStatus } from '../api/types'
import AppIcon from '../components/ui/AppIcon.vue'
import FieldSet from '../components/ui/FieldSet.vue'
import PageToolbar from '../components/ui/PageToolbar.vue'
import { formatRelative } from '../utils/time'

const status = ref<SystemStatus | null>(null)
const error = ref<string | null>(null)
let timer: number | undefined

async function refresh() {
  try {
    status.value = await api<SystemStatus>('/system/status')
    error.value = null
  } catch (exc) {
    error.value = errorMessage(exc)
  }
}

async function run(path: string) {
  await api(path, { method: 'POST' }).catch((exc) => (error.value = errorMessage(exc)))
  await refresh()
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 5000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <PageToolbar>
    <button class="btn btn-ghost" :disabled="status?.scanner.running" @click="run('/system/scan')">
      <AppIcon name="refresh" :class="{ 'animate-spin': status?.scanner.running }" />
      Scan Library
    </button>
    <button class="btn btn-ghost" @click="run('/system/rematch')">
      <AppIcon name="camera" />
      Rematch Cameras
    </button>
    <template #right>
      <span v-if="error" class="text-sm text-danger">{{ error }}</span>
    </template>
  </PageToolbar>

  <div v-if="status" class="p-4 sm:p-6">
    <FieldSet legend="About">
      <dl class="grid max-w-3xl grid-cols-[10rem_1fr] gap-y-2 text-sm">
        <dt class="text-muted">Version</dt>
        <dd>{{ status.version }}</dd>
        <dt class="text-muted">FFmpeg</dt>
        <dd class="break-all font-mono text-xs">{{ status.ffmpeg ?? 'Not found' }}</dd>
        <dt class="text-muted">Cameras</dt>
        <dd>{{ status.cameras }}</dd>
        <dt class="text-muted">Recordings</dt>
        <dd>{{ status.recordings.toLocaleString() }} ({{ status.unassigned_recordings.toLocaleString() }} unassigned)</dd>
        <dt class="text-muted">Pending thumbnails</dt>
        <dd>{{ status.pending_thumbnails.toLocaleString() }}</dd>
      </dl>
    </FieldSet>

    <FieldSet legend="Scheduled Tasks">
      <div class="overflow-x-auto rounded-md bg-panel shadow-sm">
        <table class="w-full text-left text-sm">
          <thead class="border-b border-line text-xs text-muted uppercase">
            <tr>
              <th class="px-4 py-3">Task</th>
              <th class="px-4 py-3">Interval</th>
              <th class="px-4 py-3">Last execution</th>
              <th class="px-4 py-3">Next execution</th>
              <th class="px-4 py-3">State</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-line">
              <td class="px-4 py-3">Library scan</td>
              <td class="px-4 py-3">
                {{ status.scanner.interval_minutes ? `${status.scanner.interval_minutes} min` : 'Disabled' }}
              </td>
              <td class="px-4 py-3">
                {{ status.scanner.last_scan?.finished_at ? formatRelative(status.scanner.last_scan.finished_at) : '-' }}
              </td>
              <td class="px-4 py-3">
                {{ status.scanner.next_scan_at ? formatRelative(status.scanner.next_scan_at) : '-' }}
              </td>
              <td class="px-4 py-3">
                <span class="badge" :class="status.scanner.running ? 'bg-warning text-black' : 'bg-raised'">
                  {{ status.scanner.running ? 'Running' : 'Idle' }}
                </span>
              </td>
            </tr>
            <tr>
              <td class="px-4 py-3">Thumbnail generation</td>
              <td class="px-4 py-3">Continuous</td>
              <td class="px-4 py-3">-</td>
              <td class="px-4 py-3">-</td>
              <td class="px-4 py-3">
                <span class="badge" :class="status.pending_thumbnails ? 'bg-warning text-black' : 'bg-raised'">
                  {{ status.pending_thumbnails ? `${status.pending_thumbnails} queued` : 'Idle' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </FieldSet>
  </div>
</template>
