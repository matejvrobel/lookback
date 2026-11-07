<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import PageToolbar from '../ui/PageToolbar.vue'

const props = defineProps<{ dirty: boolean; saving: boolean; error: string | null; savedAt: number | null }>()
const emit = defineEmits<{ save: []; discard: [] }>()

const justSaved = computed(() => props.savedAt !== null && !props.dirty)
</script>

<template>
  <PageToolbar>
    <button class="btn btn-ghost" :disabled="!dirty || saving" @click="emit('save')">
      <AppIcon :name="justSaved ? 'check' : 'save'" />
      {{ saving ? 'Saving…' : justSaved ? 'Saved' : 'Save Changes' }}
    </button>
    <button class="btn btn-ghost" :disabled="!dirty || saving" @click="emit('discard')">
      <AppIcon name="undo" />
      Discard
    </button>
    <slot />
    <template #right>
      <span v-if="error" class="text-sm text-danger">{{ error }}</span>
      <span v-else-if="dirty" class="text-sm text-warning">Unsaved changes</span>
    </template>
  </PageToolbar>
</template>
