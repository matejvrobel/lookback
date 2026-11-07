<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { CameraGroup } from '../../api/types'
import GroupEditModal from '../../components/settings/GroupEditModal.vue'
import AppIcon from '../../components/ui/AppIcon.vue'
import PageToolbar from '../../components/ui/PageToolbar.vue'
import { useCatalogStore } from '../../stores/catalog'

const catalog = useCatalogStore()
const editing = ref<CameraGroup | null>(null)
const modalOpen = ref(false)

function openEditor(group: CameraGroup | null) {
  editing.value = group
  modalOpen.value = true
}

onMounted(() => catalog.load(true))
</script>

<template>
  <PageToolbar>
    <button class="btn btn-ghost" @click="openEditor(null)">
      <AppIcon name="plus" />
      Add Group
    </button>
  </PageToolbar>

  <div class="p-4 sm:p-6">
    <div v-if="catalog.loaded && !catalog.groups.length" class="card text-center">
      <AppIcon name="layers" :size="40" class="mx-auto mb-3 text-muted" />
      <p class="mb-1 text-lg">No camera groups</p>
      <p class="mb-4 text-sm text-muted">Groups let you show several cameras on one timeline, e.g. "Outdoor" or "Garage".</p>
      <button class="btn btn-primary" @click="openEditor(null)">Create a group</button>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <button
        v-for="group in catalog.groups"
        :key="group.id"
        class="card text-left transition-colors hover:bg-hover"
        @click="openEditor(group)"
      >
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-medium">{{ group.name }}</h3>
          <span class="text-xs text-muted">{{ group.camera_ids.length }} camera(s)</span>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="cameraId in group.camera_ids"
            :key="cameraId"
            class="badge gap-1.5 bg-raised"
          >
            <span class="h-2 w-2 rounded-full" :style="{ background: catalog.cameraById.get(cameraId)?.color }" />
            {{ catalog.cameraById.get(cameraId)?.name ?? `#${cameraId}` }}
          </span>
          <span v-if="!group.camera_ids.length" class="text-sm text-muted">Empty group</span>
        </div>
      </button>
    </div>
  </div>

  <GroupEditModal v-if="modalOpen" :group="editing" @close="modalOpen = false" />
</template>
