<script setup lang="ts">
import { computed } from 'vue'
import type { SourceFilter } from '../../api/types'
import { useCatalogStore } from '../../stores/catalog'

const model = defineModel<SourceFilter>({ required: true })
const catalog = useCatalogStore()

const value = computed({
  get() {
    const source = model.value
    return source.kind === 'all' ? 'all' : `${source.kind}:${source.id}`
  },
  set(raw: string) {
    if (raw === 'all') {
      model.value = { kind: 'all' }
      return
    }
    const [kind, id] = raw.split(':')
    model.value = { kind: kind === 'group' ? 'group' : 'camera', id: Number(id) }
  },
})
</script>

<template>
  <select v-model="value" class="input w-auto min-w-48" aria-label="Cameras to show">
    <option value="all">All cameras</option>
    <optgroup v-if="catalog.groups.length" label="Groups">
      <option v-for="group in catalog.groups" :key="group.id" :value="`group:${group.id}`">{{ group.name }}</option>
    </optgroup>
    <optgroup v-if="catalog.cameras.length" label="Cameras">
      <option v-for="camera in catalog.cameras" :key="camera.id" :value="`camera:${camera.id}`">{{ camera.name }}</option>
    </optgroup>
  </select>
</template>
