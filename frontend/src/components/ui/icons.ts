export const ICONS = {
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  settings:
    '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  camera: '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="m16 10 6-3v10l-6-3z"/>',
  folder: '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  film: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4M3 12h18"/>',
  sliders:
    '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  'chevron-left': '<path d="m15 18-6-6 6-6"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>',
  'skip-next': '<path d="m5 5 10 7-10 7z"/><path d="M19 5v14"/>',
  'skip-prev': '<path d="M19 5 9 12l10 7z"/><path d="M5 5v14"/>',
  'zoom-in': '<circle cx="11" cy="11" r="7"/><path d="m21 21-5-5M11 8v6M8 11h6"/>',
  'zoom-out': '<circle cx="11" cy="11" r="7"/><path d="m21 21-5-5M8 11h6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  save: '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v5h8M8 21v-7h8v7"/>',
  play: '<path d="M7 4l13 8-13 8z"/>',
  check: '<path d="m5 12 5 5 9-11"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-5-5"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
} as const

export type IconName = keyof typeof ICONS
