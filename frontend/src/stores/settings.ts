import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { AppSettings, SettingsSection } from '../api/types'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<AppSettings | null>(null)
  let pending: Promise<AppSettings> | null = null

  async function load(force = false): Promise<AppSettings> {
    if (settings.value && !force) return settings.value
    pending ??= api<AppSettings>('/settings').finally(() => (pending = null))
    settings.value = await pending
    return settings.value
  }

  async function saveSection<K extends SettingsSection>(section: K, values: AppSettings[K]): Promise<AppSettings[K]> {
    const updated = await api<AppSettings[K]>(`/settings/${section}`, {
      method: 'PUT',
      body: JSON.stringify(values),
    })
    if (settings.value) settings.value[section] = updated
    return updated
  }

  async function resetSection<K extends SettingsSection>(section: K): Promise<AppSettings[K]> {
    const defaults = await api<AppSettings[K]>(`/settings/${section}`, { method: 'DELETE' })
    if (settings.value) settings.value[section] = defaults
    return defaults
  }

  return { settings, load, saveSection, resetSection }
})
