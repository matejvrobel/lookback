<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api, errorMessage } from '../../api/client'
import type { SystemStatus } from '../../api/types'
import SaveToolbar from '../../components/settings/SaveToolbar.vue'
import AppIcon from '../../components/ui/AppIcon.vue'
import FieldSet from '../../components/ui/FieldSet.vue'
import FormRow from '../../components/ui/FormRow.vue'
import ToggleSwitch from '../../components/ui/ToggleSwitch.vue'
import { useSettingsForm } from '../../composables/useSettingsForm'
import { formatRelative } from '../../utils/time'

const { draft, dirty, saving, error, savedAt, save, discard } = useSettingsForm(['scanner'])
const status = ref<SystemStatus | null>(null)
const actionError = ref<string | null>(null)
const INTERVAL_PRESETS = [0, 1, 5, 15, 30, 60, 360, 1440]
let timer: number | undefined

async function refresh() {
  try {
    status.value = await api<SystemStatus>('/system/status')
  } catch (exc) {
    actionError.value = errorMessage(exc)
  }
}

async function scanNow() {
  actionError.value = null
  await api('/system/scan', { method: 'POST' }).catch((exc) => (actionError.value = errorMessage(exc)))
  await refresh()
}

function presetLabel(minutes: number) {
  if (minutes === 0) return 'Disabled'
  if (minutes < 60) return `${minutes} min`
  return minutes === 1440 ? 'Daily' : `${minutes / 60} h`
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 3000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <SaveToolbar :dirty="dirty" :saving="saving" :error="error" :saved-at="savedAt" @save="save" @discard="discard">
    <button class="btn btn-ghost" :disabled="status?.scanner.running" @click="scanNow">
      <AppIcon name="refresh" :class="{ 'animate-spin': status?.scanner.running }" />
      {{ status?.scanner.running ? 'Scanning…' : 'Scan Now' }}
    </button>
  </SaveToolbar>

  <div v-if="draft" class="p-4 sm:p-6">
    <FieldSet legend="Schedule">
      <FormRow
        label="Scan interval"
        input-id="scan-interval"
        help="How often the root folders are re-scanned. Unchanged files are skipped, so frequent scans are cheap."
      >
        <div class="flex flex-wrap items-center gap-2">
          <input
            id="scan-interval"
            v-model.number="draft.scanner.interval_minutes"
            type="number"
            min="0"
            class="input w-28"
          />
          <span class="text-sm text-muted">minutes</span>
          <button
            v-for="preset in INTERVAL_PRESETS"
            :key="preset"
            type="button"
            class="badge cursor-pointer"
            :class="draft.scanner.interval_minutes === preset ? 'bg-accent text-white' : 'bg-raised text-muted hover:text-fg'"
            @click="draft.scanner.interval_minutes = preset"
          >
            {{ presetLabel(preset) }}
          </button>
        </div>
      </FormRow>
      <FormRow label="Scan on startup">
        <ToggleSwitch v-model="draft.scanner.scan_on_startup" />
      </FormRow>
    </FieldSet>

    <FieldSet legend="File Watcher">
      <FormRow
        label="Watch for changes"
        help="Triggers a scan shortly after new files appear. Inotify does not work on most SMB/NFS mounts."
      >
        <ToggleSwitch v-model="draft.scanner.watch_enabled" />
      </FormRow>
      <FormRow
        v-if="draft.scanner.watch_enabled"
        label="Force polling"
        help="Use polling instead of inotify; required for network shares but uses more I/O."
      >
        <ToggleSwitch v-model="draft.scanner.watch_force_polling" />
      </FormRow>
    </FieldSet>

    <FieldSet legend="Performance">
      <FormRow label="Parallel probes" input-id="probe-concurrency" help="Number of ffprobe processes run at the same time.">
        <input
          id="probe-concurrency"
          v-model.number="draft.scanner.probe_concurrency"
          type="number"
          min="1"
          max="32"
          class="input w-28"
        />
      </FormRow>
    </FieldSet>

    <FieldSet v-if="status" legend="Status">
      <p v-if="actionError" class="mb-2 text-sm text-danger">{{ actionError }}</p>
      <dl class="grid max-w-3xl grid-cols-2 gap-4 sm:grid-cols-4">
        <div class="card p-4">
          <dt class="text-xs text-muted uppercase">Recordings</dt>
          <dd class="text-xl tabular-nums">{{ status.recordings.toLocaleString() }}</dd>
        </div>
        <div class="card p-4">
          <dt class="text-xs text-muted uppercase">Unassigned</dt>
          <dd class="text-xl tabular-nums">{{ status.unassigned_recordings.toLocaleString() }}</dd>
        </div>
        <div class="card p-4">
          <dt class="text-xs text-muted uppercase">Last scan</dt>
          <dd class="text-sm">
            {{ status.scanner.last_scan?.finished_at ? formatRelative(status.scanner.last_scan.finished_at) : 'Never' }}
          </dd>
        </div>
        <div class="card p-4">
          <dt class="text-xs text-muted uppercase">Next scan</dt>
          <dd class="text-sm">
            {{ status.scanner.next_scan_at ? formatRelative(status.scanner.next_scan_at) : 'Not scheduled' }}
          </dd>
        </div>
      </dl>
      <p v-if="status.scanner.last_scan" class="mt-3 text-sm text-muted">
        Last run: {{ status.scanner.last_scan.files_seen }} files seen, {{ status.scanner.last_scan.added }} added,
        {{ status.scanner.last_scan.updated }} updated, {{ status.scanner.last_scan.removed }} removed,
        {{ status.scanner.last_scan.errors }} errors.
        <span v-if="status.scanner.last_scan.unavailable_roots.length" class="text-warning">
          Unavailable: {{ status.scanner.last_scan.unavailable_roots.join(', ') }}
        </span>
      </p>
    </FieldSet>
  </div>
</template>
