<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { api, errorMessage } from '../../api/client'
import type { Camera, CameraInput, MatchTestResult, MatchType } from '../../api/types'
import { useCatalogStore } from '../../stores/catalog'
import AppIcon from '../ui/AppIcon.vue'
import FormRow from '../ui/FormRow.vue'
import ModalDialog from '../ui/ModalDialog.vue'
import ToggleSwitch from '../ui/ToggleSwitch.vue'

const props = defineProps<{ camera: Camera | null }>()
const emit = defineEmits<{ close: [] }>()
const catalog = useCatalogStore()

const MATCH_TYPES: { value: MatchType; label: string; placeholder: string; help: string }[] = [
  {
    value: 'folder',
    label: 'Folder',
    placeholder: 'FrontDoor',
    help: 'A folder name anywhere in the path, or a path prefix like "NVR/FrontDoor".',
  },
  { value: 'prefix', label: 'Filename prefix', placeholder: 'front_', help: 'Matches files whose name starts with this text.' },
  {
    value: 'regex',
    label: 'Regex',
    placeholder: '^garage/.*\\.mkv$',
    help: 'Case-insensitive regular expression searched in the relative path (forward slashes).',
  },
]

const form = reactive<CameraInput>({
  name: props.camera?.name ?? '',
  match_type: props.camera?.match_type ?? 'folder',
  match_value: props.camera?.match_value ?? '',
  timestamp_regex: props.camera?.timestamp_regex ?? null,
  color: props.camera?.color ?? '#4f9fe8',
  priority: props.camera?.priority ?? 100,
  sort_order: props.camera?.sort_order ?? catalog.cameras.length,
  enabled: props.camera?.enabled ?? true,
})

const saving = ref(false)
const error = ref<string | null>(null)
const testing = ref(false)
const testResult = ref<MatchTestResult | null>(null)
const matchType = computed(() => MATCH_TYPES.find((type) => type.value === form.match_type)!)
const canSave = computed(() => form.name.trim() && form.match_value.trim() && !saving.value)

async function testMatch() {
  testing.value = true
  error.value = null
  try {
    testResult.value = await api<MatchTestResult>('/cameras/test-match', {
      method: 'POST',
      body: JSON.stringify({ match_type: form.match_type, match_value: form.match_value }),
    })
  } catch (exc) {
    error.value = errorMessage(exc)
  } finally {
    testing.value = false
  }
}

async function submit() {
  saving.value = true
  error.value = null
  try {
    await catalog.saveCamera({ ...form, timestamp_regex: form.timestamp_regex?.trim() || null }, props.camera?.id)
    emit('close')
  } catch (exc) {
    error.value = errorMessage(exc)
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!props.camera || !window.confirm(`Delete camera "${props.camera.name}"? Recordings stay indexed as unassigned.`)) return
  try {
    await catalog.deleteCamera(props.camera.id)
    emit('close')
  } catch (exc) {
    error.value = errorMessage(exc)
  }
}
</script>

<template>
  <ModalDialog :title="camera ? `Edit Camera - ${camera.name}` : 'Add Camera'" @close="emit('close')">
    <form id="camera-form" @submit.prevent="submit">
      <FormRow label="Name" input-id="camera-name">
        <input id="camera-name" v-model="form.name" class="input" required maxlength="100" />
      </FormRow>
      <FormRow label="Match by">
        <div class="inline-flex overflow-hidden rounded border border-line">
          <button
            v-for="type in MATCH_TYPES"
            :key="type.value"
            type="button"
            class="px-3 py-1.5 text-sm transition-colors"
            :class="form.match_type === type.value ? 'bg-accent text-white' : 'bg-canvas text-muted hover:text-fg'"
            @click="form.match_type = type.value; testResult = null"
          >
            {{ type.label }}
          </button>
        </div>
      </FormRow>
      <FormRow :label="matchType.label" :help="matchType.help" input-id="camera-match">
        <div class="flex gap-2">
          <input
            id="camera-match"
            v-model="form.match_value"
            class="input font-mono text-xs"
            :placeholder="matchType.placeholder"
            required
            @input="testResult = null"
          />
          <button type="button" class="btn btn-default" :disabled="!form.match_value.trim() || testing" @click="testMatch">
            <AppIcon name="search" :size="16" />
            Test
          </button>
        </div>
        <div v-if="testResult" class="mt-2 rounded border border-line bg-canvas p-2 text-xs">
          <p class="mb-1 font-medium" :class="testResult.matched ? 'text-success' : 'text-warning'">
            {{ testResult.matched }} indexed file(s) match
          </p>
          <p v-for="sample in testResult.samples" :key="sample" class="truncate font-mono text-muted">{{ sample }}</p>
        </div>
      </FormRow>
      <FormRow
        label="Timestamp regex"
        input-id="camera-ts"
        help="Optional override tried before the global patterns, e.g. (?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})_(?P<H>\d{2})(?P<M>\d{2})(?P<S>\d{2})"
      >
        <input id="camera-ts" v-model="form.timestamp_regex" class="input font-mono text-xs" />
      </FormRow>
      <FormRow label="Color" input-id="camera-color">
        <div class="flex items-center gap-2">
          <input id="camera-color" v-model="form.color" type="color" class="h-8 w-12 cursor-pointer rounded border border-line bg-canvas" />
          <input v-model="form.color" class="input w-32 font-mono text-xs" pattern="#[0-9a-fA-F]{6}" />
        </div>
      </FormRow>
      <FormRow label="Priority" input-id="camera-priority" help="Lower values are matched first when several cameras could claim a file.">
        <input id="camera-priority" v-model.number="form.priority" type="number" class="input w-32" />
      </FormRow>
      <FormRow label="Sort order" input-id="camera-sort">
        <input id="camera-sort" v-model.number="form.sort_order" type="number" class="input w-32" />
      </FormRow>
      <FormRow label="Enabled">
        <ToggleSwitch v-model="form.enabled" />
      </FormRow>
    </form>

    <template #footer>
      <button v-if="camera" type="button" class="btn btn-danger" @click="remove">
        <AppIcon name="trash" :size="16" />
        Delete
      </button>
      <span v-if="error" class="text-sm text-danger">{{ error }}</span>
      <div class="ml-auto flex gap-2">
        <button type="button" class="btn btn-default" @click="emit('close')">Cancel</button>
        <button type="submit" form="camera-form" class="btn btn-primary" :disabled="!canSave">
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </template>
  </ModalDialog>
</template>
