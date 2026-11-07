import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { errorMessage } from '../api/client'
import type { AppSettings, SettingsSection } from '../api/types'
import { useSettingsStore } from '../stores/settings'

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

export function useSettingsForm<K extends SettingsSection>(sections: K[]) {
  const store = useSettingsStore()
  const draft = ref(null) as Ref<Pick<AppSettings, K> | null>
  const saving = ref(false)
  const error = ref<string | null>(null)
  const savedAt = ref<number | null>(null)

  const snapshot = computed(() => {
    const settings = store.settings
    if (!settings) return null
    return Object.fromEntries(sections.map((section) => [section, settings[section]])) as Pick<AppSettings, K>
  })

  watch(snapshot, (value) => (draft.value = value ? clone(value) : null), { immediate: true })

  const dirtySections = computed(() => {
    const current = draft.value
    const original = snapshot.value
    if (!current || !original) return []
    return sections.filter((section) => JSON.stringify(current[section]) !== JSON.stringify(original[section]))
  })
  const dirty = computed(() => dirtySections.value.length > 0)

  async function save() {
    if (!draft.value || !dirty.value) return
    const pending = dirtySections.value.map((section) => [section, clone(draft.value![section])] as const)
    saving.value = true
    error.value = null
    try {
      for (const [section, values] of pending) await store.saveSection(section, values)
      savedAt.value = Date.now()
    } catch (exc) {
      error.value = errorMessage(exc)
    } finally {
      saving.value = false
    }
  }

  function discard() {
    draft.value = snapshot.value ? clone(snapshot.value) : null
    error.value = null
  }

  onMounted(() => {
    store.load().catch((exc) => (error.value = errorMessage(exc)))
  })

  onBeforeRouteLeave(() => !dirty.value || window.confirm('You have unsaved changes. Leave this page anyway?'))

  return { draft, dirty, saving, error, savedAt, save, discard }
}
