export type MatchType = 'folder' | 'prefix' | 'regex'
export type PlaybackRate = 1 | 2 | 4 | 8

export interface Camera {
  id: number
  name: string
  match_type: MatchType
  match_value: string
  timestamp_regex: string | null
  color: string
  priority: number
  sort_order: number
  enabled: boolean
  recording_count: number
}

export type CameraInput = Omit<Camera, 'id' | 'recording_count'>

export interface CameraGroup {
  id: number
  name: string
  sort_order: number
  camera_ids: number[]
}

export type GroupInput = Omit<CameraGroup, 'id'>

export interface MatchTestResult {
  matched: number
  samples: string[]
}

export interface GeneralSettings {
  instance_name: string
  timezone: string
}

export interface LibrarySettings {
  root_folders: string[]
  extensions: string[]
  ignore_patterns: string[]
  min_file_age_seconds: number
  remove_missing: boolean
  timestamp_patterns: string[]
}

export interface ScannerSettings {
  interval_minutes: number
  scan_on_startup: boolean
  watch_enabled: boolean
  watch_force_polling: boolean
  probe_concurrency: number
}

export interface PlaybackSettings {
  mode: 'auto' | 'transcode'
  direct_video_codecs: string[]
  direct_audio_codecs: string[]
  cache_size_mb: number
  hls_idle_timeout_seconds: number
}

export interface FFmpegSettings {
  ffmpeg_path: string
  ffprobe_path: string
  hwaccel: 'none' | 'vaapi' | 'qsv' | 'nvenc'
  hwaccel_device: string
  video_preset: string
  video_quality: number
  audio_bitrate: string
  hls_segment_seconds: number
  extra_input_args: string[]
  extra_output_args: string[]
}

export interface ThumbnailSettings {
  enabled: boolean
  interval_seconds: number
  max_per_clip: number
  sprite_width: number
  poster_width: number
  quality: number
  concurrency: number
}

export interface UISettings {
  theme: 'dark' | 'light' | 'system'
  first_day_of_week: 0 | 1
  time_format: '24h' | '12h'
  default_playback_rate: PlaybackRate
  autoplay_next: boolean
  timeline_gap_merge_seconds: number
  timeline_show_thumbnails: boolean
}

export interface AppSettings {
  general: GeneralSettings
  library: LibrarySettings
  scanner: ScannerSettings
  playback: PlaybackSettings
  ffmpeg: FFmpegSettings
  thumbnails: ThumbnailSettings
  ui: UISettings
}

export type SettingsSection = keyof AppSettings

export interface TimelineClip {
  id: number
  start: number
  end: number
  thumb_ready: boolean
  thumb_count: number
  thumb_interval: number | null
}

export interface TimelineSpan {
  start: number
  end: number
  clip_count: number
}

export interface TimelineLane {
  camera_id: number | null
  name: string
  color: string
  spans: TimelineSpan[]
  clips: TimelineClip[]
}

export interface TimelineData {
  date: string
  timezone: string
  day_start: number
  day_end: number
  lanes: TimelineLane[]
}

export interface CalendarDay {
  date: string
  clips: number
  duration: number
  camera_ids: (number | null)[]
}

export interface CalendarBounds {
  first_day: string | null
  last_day: string | null
}

export interface Recording {
  id: number
  camera_id: number | null
  rel_path: string
  size: number
  start_ts: number
  end_ts: number
  duration: number
  day: string
  container: string
  video_codec: string | null
  audio_codec: string | null
  width: number | null
  height: number | null
  thumb_status: 'pending' | 'done' | 'failed'
  thumb_count: number
  thumb_interval: number | null
}

export interface AdjacentRecordings {
  previous: Recording | null
  next: Recording | null
  gap_before: number | null
  gap_after: number | null
}

export interface PlaybackInfo {
  recording_id: number
  method: 'direct' | 'remux' | 'hls'
  url: string
  mime_type: string
}

export interface ScanStats {
  started_at: number
  finished_at: number | null
  files_seen: number
  added: number
  updated: number
  removed: number
  errors: number
  unavailable_roots: string[]
}

export interface SystemStatus {
  version: string
  ffmpeg: string | null
  recordings: number
  unassigned_recordings: number
  pending_thumbnails: number
  cameras: number
  scanner: {
    running: boolean
    interval_minutes: number
    next_scan_at: number | null
    last_scan: ScanStats | null
  }
}

export type SourceFilter = { kind: 'all' } | { kind: 'camera'; id: number } | { kind: 'group'; id: number }

export interface PlayableClip {
  id: number
  start: number
  end: number
  cameraId: number | null
  label: string
}

export interface PlayRequest {
  clip: PlayableClip
  offset: number
  token: number
}
