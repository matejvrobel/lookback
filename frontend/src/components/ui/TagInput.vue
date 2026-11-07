<script setup lang="ts">
import { ref } from 'vue'

const model = defineModel<string[]>({ required: true })
withDefaults(defineProps<{ placeholder?: string }>(), { placeholder: 'Type and press Enter' })

const pending = ref('')

function commit() {
  const values = pending.value
    .split(',')
    .map((value) => value.trim())
    .filter((value) => value && !model.value.includes(value))
  if (values.length) model.value = [...model.value, ...values]
  pending.value = ''
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    commit()
  } else if (event.key === 'Backspace' && !pending.value && model.value.length) {
    model.value = model.value.slice(0, -1)
  }
}
</script>

<template>
  <div class="input flex flex-wrap items-center gap-1.5 py-1">
    <span v-for="tag in model" :key="tag" class="badge gap-1 bg-raised text-fg">
      {{ tag }}
      <button type="button" class="text-muted hover:text-fg" @click="model = model.filter((item) => item !== tag)">×</button>
    </span>
    <input
      v-model="pending"
      class="min-w-24 flex-1 bg-transparent py-0.5 text-sm outline-none"
      :placeholder="placeholder"
      @keydown="onKeydown"
      @blur="commit"
    />
  </div>
</template>
