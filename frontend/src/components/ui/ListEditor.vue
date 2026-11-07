<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from './AppIcon.vue'

const model = defineModel<string[]>({ required: true })
withDefaults(defineProps<{ placeholder?: string; monospace?: boolean }>(), { placeholder: '', monospace: false })

const pending = ref('')

function add() {
  const value = pending.value.trim()
  if (!value || model.value.includes(value)) return
  model.value = [...model.value, value]
  pending.value = ''
}

function update(index: number, value: string) {
  const next = [...model.value]
  next[index] = value
  model.value = next
}

function remove(index: number) {
  model.value = model.value.filter((_, position) => position !== index)
}
</script>

<template>
  <div class="space-y-2">
    <div v-for="(item, index) in model" :key="index" class="flex gap-2">
      <input
        class="input"
        :class="{ 'font-mono text-xs': monospace }"
        :value="item"
        @change="update(index, ($event.target as HTMLInputElement).value)"
      />
      <button type="button" class="btn btn-ghost px-2" title="Remove" @click="remove(index)">
        <AppIcon name="x" :size="16" />
      </button>
    </div>
    <div class="flex gap-2">
      <input
        v-model="pending"
        class="input"
        :class="{ 'font-mono text-xs': monospace }"
        :placeholder="placeholder"
        @keydown.enter.prevent="add"
      />
      <button type="button" class="btn btn-default px-2" title="Add" :disabled="!pending.trim()" @click="add">
        <AppIcon name="plus" :size="16" />
      </button>
    </div>
  </div>
</template>
