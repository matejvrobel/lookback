import { createRouter, createWebHistory, type RouteComponent } from 'vue-router'
import { settingsSections, type SettingsKey } from './navigation'

const settingsPages: Record<SettingsKey, () => Promise<RouteComponent>> = {
  library: () => import('./views/settings/SettingsLibrary.vue'),
  cameras: () => import('./views/settings/SettingsCameras.vue'),
  groups: () => import('./views/settings/SettingsGroups.vue'),
  scanner: () => import('./views/settings/SettingsScanner.vue'),
  playback: () => import('./views/settings/SettingsPlayback.vue'),
  general: () => import('./views/settings/SettingsGeneral.vue'),
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/calendar' },
    {
      path: '/calendar',
      name: 'calendar',
      component: () => import('./views/PlaybackView.vue'),
      meta: { title: 'Calendar' },
    },
    {
      path: '/settings',
      component: () => import('./views/SettingsView.vue'),
      redirect: '/settings/library',
      children: settingsSections.map((section) => ({
        path: section.key,
        name: `settings-${section.key}`,
        component: settingsPages[section.key],
        meta: { title: `${section.label} Settings` },
      })),
    },
    {
      path: '/system',
      name: 'system',
      component: () => import('./views/SystemView.vue'),
      meta: { title: 'System' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/calendar' },
  ],
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : null
  document.title = title ? `${title} - RecordViewer` : 'RecordViewer'
})
