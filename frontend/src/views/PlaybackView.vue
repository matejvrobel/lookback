<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'
import { api, buildQuery, errorMessage, sourceParams } from '../api/client'
import type {
  AdjacentRecordings,
  CalendarBounds,
  CalendarDay,
  PlayableClip,
  PlaybackRate,
  PlayRequest,
  SourceFilter,
  TimelineClip,
  TimelineData,
  TimelineLane,
} from '../api/types'
import DayTimeline from '../components/playback/DayTimeline.vue'
import MonthCalendar from '../components/playback/MonthCalendar.vue'
import SourceSelector from '../components/playback/SourceSelector.vue'
import VideoPlayer from '../components/playback/VideoPlayer.vue'
import AppIcon from '../components/ui/AppIcon.vue'
import PageToolbar from '../components/ui/PageToolbar.vue'
import { useCatalogStore } from '../stores/catalog'
import { useSettingsStore } from '../stores/settings'
import { formatDateLong, formatDuration, isoDateIn, shiftDate, todayIn } from '../utils/time'

const route = useRoute()
const router = useRouter()
const settingsStore = useSettingsStore()
const catalog = useCatalogStore()

const ready = ref(false)
const loadError = ref<string | null>(null)
const source = ref<SourceFilter>({ kind: 'all' })
const selectedDate = ref('')
const viewYear = ref(2000)
const viewMonth = ref(1)
const timeline = ref<TimelineData | null>(null)
const timelineLoading = ref(false)
const timelineError = ref<string | null>(null)
const calendarDays = ref<CalendarDay[]>([])
const calendarLoading = ref(false)
const request = ref<PlayRequest | null>(null)
const currentClip = ref<PlayableClip | null>(null)
const playhead = ref<number | null>(null)
const autoplay = ref(true)
const rate = ref<PlaybackRate>(1)
let timelineToken = 0
let calendarToken = 0

const ui = computed(() => settingsStore.settings?.ui)
const timeZone = computed(() => timeline.value?.timezone ?? settingsStore.settings?.general.timezone ?? 'UTC')
const hour12 = computed(() => ui.value?.time_format === '12h')
const today = computed(() => todayIn(timeZone.value))
const sourceKey = computed(() => JSON.stringify(source.value))
const daySummary = computed(() => {
  const lanes = timeline.value?.lanes ?? []
  const clips = lanes.reduce((sum, lane) => sum + lane.clips.length, 0)
  const seconds = lanes.reduce((sum, lane) => sum + lane.clips.reduce((total, clip) => total + clip.end - clip.start, 0), 0)
  return { clips, seconds, cameras: lanes.filter((lane) => lane.clips.length).length }
})

function parseSource(query: LocationQuery): SourceFilter {
  const camera = Number(query.camera)
  if (Number.isInteger(camera) && camera > 0) return { kind: 'camera', id: camera }
  const group = Number(query.group)
  if (Number.isInteger(group) && group > 0) return { kind: 'group', id: group }
  return { kind: 'all' }
}

function selectDate(date: string) {
  selectedDate.value = date
  const [year, month] = date.split('-').map(Number)
  viewYear.value = year
  viewMonth.value = month
}

async function loadTimeline() {
  const token = ++timelineToken
  timelineLoading.value = true
  timelineError.value = null
  try {
    const data = await api<TimelineData>(`/timeline${buildQuery({ date: selectedDate.value, ...sourceParams(source.value) })}`)
    if (token === timelineToken) timeline.value = data
  } catch (error) {
    if (token === timelineToken) timelineError.value = errorMessage(error)
  } finally {
    if (token === timelineToken) timelineLoading.value = false
  }
}

async function loadCalendar() {
  const token = ++calendarToken
  calendarLoading.value = true
  try {
    const days = await api<CalendarDay[]>(
      `/calendar${buildQuery({ year: viewYear.value, month: viewMonth.value, ...sourceParams(source.value) })}`,
    )
    if (token === calendarToken) calendarDays.value = days
  } catch {
    if (token === calendarToken) calendarDays.value = []
  } finally {
    if (token === calendarToken) calendarLoading.value = false
  }
}

function toPlayable(lane: TimelineLane, clip: TimelineClip): PlayableClip {
  return { id: clip.id, start: clip.start, end: clip.end, cameraId: lane.camera_id, label: lane.name }
}

function startPlayback(clip: PlayableClip, offset: number) {
  currentClip.value = clip
  request.value = { clip, offset, token: (request.value?.token ?? 0) + 1 }
}

function onSeek({ lane, ts }: { lane: TimelineLane; ts: number }) {
  const containing = lane.clips.find((clip) => clip.start <= ts && ts < clip.end)
  const target = containing ?? lane.clips.find((clip) => clip.start > ts)
  if (target) startPlayback(toPlayable(lane, target), containing ? ts - target.start : 0)
}

async function neighbour(clip: PlayableClip, direction: 1 | -1): Promise<PlayableClip | null> {
  const lane = timeline.value?.lanes.find((candidate) => candidate.camera_id === clip.cameraId)
  const index = lane ? lane.clips.findIndex((candidate) => candidate.id === clip.id) : -1
  if (lane && index >= 0 && lane.clips[index + direction]) return toPlayable(lane, lane.clips[index + direction])

  const adjacent = await api<AdjacentRecordings>(`/recordings/${clip.id}/adjacent`)
  const recording = direction > 0 ? adjacent.next : adjacent.previous
  if (!recording) return null
  return {
    id: recording.id,
    start: recording.start_ts,
    end: recording.end_ts,
    cameraId: recording.camera_id,
    label: recording.camera_id === null ? 'Unassigned' : (catalog.cameraById.get(recording.camera_id)?.name ?? clip.label),
  }
}

const resolveNext = (clip: PlayableClip) => neighbour(clip, 1)
const resolvePrevious = (clip: PlayableClip) => neighbour(clip, -1)

function onClipChange(clip: PlayableClip) {
  currentClip.value = clip
  const day = timeline.value
  if (day && (clip.start >= day.day_end || clip.end <= day.day_start)) selectDate(isoDateIn(clip.start, timeZone.value))
}

function onNavigateMonth(year: number, month: number) {
  viewYear.value = year
  viewMonth.value = month
}

watch([selectedDate, sourceKey], () => {
  if (!selectedDate.value) return
  loadTimeline()
  const query: Record<string, string> = { date: selectedDate.value }
  if (source.value.kind !== 'all') query[source.value.kind] = String(source.value.id)
  router.replace({ query })
})

watch([viewYear, viewMonth, sourceKey], () => {
  if (ready.value) loadCalendar()
})

onMounted(async () => {
  try {
    const settings = await settingsStore.load()
    await catalog.load()
    autoplay.value = settings.ui.autoplay_next
    rate.value = settings.ui.default_playback_rate
    source.value = parseSource(route.query)

    const queryDate = typeof route.query.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(route.query.date) ? route.query.date : null
    let date = queryDate ?? todayIn(settings.general.timezone)
    if (!queryDate) {
      const bounds = await api<CalendarBounds>(`/calendar/bounds${buildQuery(sourceParams(source.value))}`).catch(() => null)
      if (bounds?.last_day && bounds.last_day < date) date = bounds.last_day
    }
    ready.value = true
    selectDate(date)
  } catch (error) {
    loadError.value = errorMessage(error)
  }
})
</script>

<template>
  <div class="flex min-h-full flex-col">
    <PageToolbar>
      <SourceSelector v-model="source" />
      <div class="flex items-center gap-1">
        <button class="btn btn-ghost px-2" title="Previous day" :disabled="!ready" @click="selectDate(shiftDate(selectedDate, -1))">
          <AppIcon name="chevron-left" />
        </button>
        <span class="min-w-0 px-1 text-sm font-medium whitespace-nowrap">
          {{ selectedDate ? formatDateLong(selectedDate) : '…' }}
        </span>
        <button class="btn btn-ghost px-2" title="Next day" :disabled="!ready" @click="selectDate(shiftDate(selectedDate, 1))">
          <AppIcon name="chevron-right" />
        </button>
        <button class="btn btn-ghost text-sm" :disabled="!ready || selectedDate === today" @click="selectDate(today)">
          Today
        </button>
      </div>
      <template #right>
        <span v-if="timeline" class="text-sm text-muted">
          {{ daySummary.clips }} clips · {{ daySummary.cameras }} camera(s) · {{ formatDuration(daySummary.seconds) }}
        </span>
      </template>
    </PageToolbar>

    <div v-if="loadError" class="m-6 card text-danger">{{ loadError }}</div>

    <div v-else class="grid grid-cols-1 gap-4 p-4 sm:p-6 xl:grid-cols-[20rem_minmax(0,1fr)]">
      <div class="grid content-start gap-4 md:grid-cols-[20rem_minmax(0,1fr)] xl:grid-cols-1">
        <MonthCalendar
          :year="viewYear"
          :month="viewMonth"
          :selected="selectedDate"
          :today="today"
          :days="calendarDays"
          :first-day-of-week="ui?.first_day_of_week ?? 1"
          :loading="calendarLoading"
          @select="selectDate"
          @navigate="onNavigateMonth"
        />
        <div v-if="currentClip" class="card p-4 text-sm">
          <p class="mb-1 text-xs text-muted uppercase">Now playing</p>
          <p class="font-medium">{{ currentClip.label }}</p>
          <p class="text-muted">Clip #{{ currentClip.id }} · {{ formatDuration(currentClip.end - currentClip.start) }}</p>
        </div>
      </div>

      <VideoPlayer
        v-model:autoplay="autoplay"
        v-model:rate="rate"
        :request="request"
        :time-zone="timeZone"
        :hour12="hour12"
        :resolve-next="resolveNext"
        :resolve-previous="resolvePrevious"
        @clip-change="onClipChange"
        @time="playhead = $event"
      />

      <div class="xl:col-span-2">
        <div v-if="timelineError" class="card text-sm text-danger">{{ timelineError }}</div>
        <div v-else-if="!timeline" class="card animate-pulse text-sm text-muted">Loading timeline…</div>
        <div v-else :class="{ 'opacity-60 transition-opacity': timelineLoading }">
          <DayTimeline
            :data="timeline"
            :current-clip-id="currentClip?.id ?? null"
            :playhead="playhead"
            :hour12="hour12"
            :show-thumbnails="ui?.timeline_show_thumbnails ?? true"
            @seek="onSeek"
          />
          <p v-if="!daySummary.clips" class="mt-3 text-center text-sm text-muted">
            No recordings on this day for the selected cameras.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
