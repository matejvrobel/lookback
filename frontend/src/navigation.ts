import type { IconName } from './components/ui/icons'

export interface NavItem {
  label: string
  to: string
  icon: IconName
}

export const settingsSections = [
  { key: 'library', label: 'Library', icon: 'folder' },
  { key: 'cameras', label: 'Cameras', icon: 'camera' },
  { key: 'groups', label: 'Groups', icon: 'layers' },
  { key: 'scanner', label: 'Scanner', icon: 'clock' },
  { key: 'playback', label: 'Playback', icon: 'film' },
  { key: 'general', label: 'General', icon: 'sliders' },
] as const satisfies readonly { key: string; label: string; icon: IconName }[]

export type SettingsKey = (typeof settingsSections)[number]['key']

export const mainNavigation: (NavItem & { children?: NavItem[] })[] = [
  { label: 'Calendar', to: '/calendar', icon: 'calendar' },
  {
    label: 'Settings',
    to: '/settings',
    icon: 'settings',
    children: settingsSections.map((section) => ({
      label: section.label,
      to: `/settings/${section.key}`,
      icon: section.icon,
    })),
  },
  { label: 'System', to: '/system', icon: 'activity' },
]
