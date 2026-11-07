<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { errorMessage } from '../../api/client'
import type { CameraGroup, GroupInput } from '../../api/types'
import { useCatalogStore } from '../../stores/catalog'
import AppIcon from '../ui/AppIcon.vue'
import FormRow from '../ui/FormRow.vue'
import ModalDialog from '../ui/ModalDialog.vue'

const props = defineProps<{ group: CameraGroup | null }>()
const emit = defineEmits<{ close: [] }>()
const catalog = useCatalogStore()

const form = reactive<GroupInput>({
  name: props.group?.name ?? '',
  sort_order: props.group?.sort_order ?? catalog.groups.length,
  camera_ids: [...(props.group?.camera_ids ?? [])],
})
const saving = ref(false)
const error = ref<string | null>(null)
const allSelected = computed(() => catalog.cameras.length > 0 && form.camera_ids.length === catalog.cameras.length)

function toggleAll() {
  form.camera_ids = allSelected.value ? [] : catalog.cameras.map((camera) => camera.id)
}

async function submit() {
  saving.value = true
  error.value = null
  try {
    await catalog.saveGroup(form, props.group?.id)
    emit('close')
  } catch (exc) {
    error.value = errorMessage(exc)
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!props.group || !window.confirm(`Delete group "${props.group.name}"? Cameras are not affected.`)) return
  try {
    await catalog.deleteGroup(props.group.id)
    emit('close')
  } catch (exc) {
    error.value = errorMessage(exc)
  }
}
</script>

<template>
  <ModalDialog :title="group ? `Edit Group - ${group.name}` : 'Add Group'" width="max-w-xl" @close="emit('close')">
    <form id="group-form" @submit.prevent="submit">
      <FormRow label="Name" input-id="group-name">
        <input id="group-name" v-model="form.name" class="input" required maxlength="100" />
      </FormRow>
      <FormRow label="Sort order" input-id="group-sort">
        <input id="group-sort" v-model.number="form.sort_order" type="number" class="input w-32" />
      </FormRow>
      <FormRow label="Cameras">
        <p v-if="!catalog.cameras.length" class="pt-1.5 text-sm text-muted">Define cameras first.</p>
        <div v-else class="rounded border border-line bg-canvas">
          <label class="flex items-center gap-3 border-b border-line px-3 py-2 text-sm text-muted">
            <input type="checkbox" :checked="allSelected" class="accent-(--rv-accent)" @change="toggleAll" />
            Select all
          </label>
          <label
            v-for="camera in catalog.cameras"
            :key="camera.id"
            class="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-hover"
          >
            <input v-model="form.camera_ids" type="checkbox" :value="camera.id" class="accent-(--rv-accent)" />
            <span class="h-2.5 w-2.5 rounded-full" :style="{ background: camera.color }" />
            {{ camera.name }}
          </label>
        </div>
      </FormRow>
    </form>

    <template #footer>
      <button v-if="group" type="button" class="btn btn-danger" @click="remove">
        <AppIcon name="trash" :size="16" />
        Delete
      </button>
      <span v-if="error" class="text-sm text-danger">{{ error }}</span>
      <div class="ml-auto flex gap-2">
        <button type="button" class="btn btn-default" @click="emit('close')">Cancel</button>
        <button type="submit" form="group-form" class="btn btn-primary" :disabled="!form.name.trim() || saving">
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </template>
  </ModalDialog>
</template>
