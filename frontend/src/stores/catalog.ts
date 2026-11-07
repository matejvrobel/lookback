import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { Camera, CameraGroup, CameraInput, GroupInput } from '../api/types'

export const useCatalogStore = defineStore('catalog', () => {
  const cameras = ref<Camera[]>([])
  const groups = ref<CameraGroup[]>([])
  const loaded = ref(false)

  const cameraById = computed(() => new Map(cameras.value.map((camera) => [camera.id, camera])))

  async function load(force = false) {
    if (loaded.value && !force) return
    const [cameraList, groupList] = await Promise.all([api<Camera[]>('/cameras'), api<CameraGroup[]>('/groups')])
    cameras.value = cameraList
    groups.value = groupList
    loaded.value = true
  }

  async function saveCamera(input: CameraInput, id?: number) {
    await api<Camera>(id ? `/cameras/${id}` : '/cameras', {
      method: id ? 'PATCH' : 'POST',
      body: JSON.stringify(input),
    })
    await load(true)
  }

  async function deleteCamera(id: number) {
    await api(`/cameras/${id}`, { method: 'DELETE' })
    await load(true)
  }

  async function saveGroup(input: GroupInput, id?: number) {
    await api<CameraGroup>(id ? `/groups/${id}` : '/groups', {
      method: id ? 'PATCH' : 'POST',
      body: JSON.stringify(input),
    })
    await load(true)
  }

  async function deleteGroup(id: number) {
    await api(`/groups/${id}`, { method: 'DELETE' })
    await load(true)
  }

  return { cameras, groups, loaded, cameraById, load, saveCamera, deleteCamera, saveGroup, deleteGroup }
})
