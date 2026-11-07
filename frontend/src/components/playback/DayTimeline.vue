<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { media } from '../../api/client'
import type { TimelineClip, TimelineData, TimelineLane } from '../../api/types'
import { formatClock } from '../../utils/time'
import AppIcon from '../ui/AppIcon.vue'

const props = defineProps<{
  data: TimelineData
  currentClipId: number | null
  playhead: number | null
  hour12: boolean
  showThumbnails: boolean
}>()
const emit = defineEmits<{ seek: [payload: { lane: TimelineLane; ts: number }] }>()

const MIN_ZOOM = 1
const MAX_ZOOM = 96
const TICK_STEPS = [60, 300, 600, 900, 1800, 3600, 7200, 10800, 21600]
const MIN_TICK_SPACING = 64
const INLINE_THUMB_WIDTH = 72
const PREVIEW_WIDTH = 192

const scroller = ref<HTMLElement | null>(null)
const viewportWidth = ref(800)
const scrollLeft = ref(0)
const zoom = ref(1)
const hover = ref<{ lane: TimelineLane; ts: number; x: number; clip: TimelineClip | null; clientX: number; top: number } | null>(
  null,
)
let resizeObserver: ResizeObserver | null = null

const daySeconds = computed(() => props.data.day_end - props.data.day_start)
const trackWidth = computed(() => viewportWidth.value * zoom.value)
const pxPerSec = computed(() => trackWidth.value / daySeconds.value)
const xOf = (ts: number) => (ts - props.data.day_start) * pxPerSec.value
const tsAt = (x: number) => props.data.day_start + x / pxPerSec.value

const totalClips = computed(() => props.data.lanes.reduce((sum, lane) => sum + lane.clips.length, 0))
const typicalClipSeconds = computed(() => {
  const durations = props.data.lanes.flatMap((lane) => lane.clips.map((clip) => clip.end - clip.start)).sort((a, b) => a - b)
  return durations.length ? durations[Math.floor(durations.length / 2)] : 0
})
const showClips = computed(() => typicalClipSeconds.value * pxPerSec.value >= 14)

const visibleRange = computed(() => {
  const margin = viewportWidth.value / 2
  return { start: tsAt(scrollLeft.value - margin), end: tsAt(scrollLeft.value + viewportWidth.value + margin) }
})

const ticks = computed(() => {
  const step = TICK_STEPS.find((candidate) => candidate * pxPerSec.value >= MIN_TICK_SPACING) ?? 21600
  const result: { ts: number; x: number; label: string; major: boolean }[] = []
  for (let ts = props.data.day_start; ts < props.data.day_end; ts += step) {
    result.push({
      ts,
      x: xOf(ts),
      label: formatClock(ts, props.data.timezone, props.hour12),
      major: (ts - props.data.day_start) % 3600 === 0,
    })
  }
  return result
})

function visibleClips(lane: TimelineLane): TimelineClip[] {
  const { start, end } = visibleRange.value
  return lane.clips.filter((clip) => clip.end > start && clip.start < end)
}

function clipAt(lane: TimelineLane, ts: number): TimelineClip | null {
  let low = 0
  let high = lane.clips.length - 1
  let found = -1
  while (low <= high) {
    const mid = (low + high) >> 1
    if (lane.clips[mid].start <= ts) {
      found = mid
      low = mid + 1
    } else {
      high = mid - 1
    }
  }
  const clip = found >= 0 ? lane.clips[found] : null
  return clip && ts < clip.end ? clip : null
}

function laneX(event: MouseEvent): number {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  return Math.min(Math.max(event.clientX - rect.left, 0), rect.width)
}

function onMove(lane: TimelineLane, event: MouseEvent) {
  const x = laneX(event)
  const ts = tsAt(x)
  const rowTop = (event.currentTarget as HTMLElement).getBoundingClientRect().top
  hover.value = { lane, ts, x, clip: clipAt(lane, ts), clientX: event.clientX, top: rowTop }
}

function onClick(lane: TimelineLane, event: MouseEvent) {
  emit('seek', { lane, ts: tsAt(laneX(event)) })
}

function spriteStyle(clip: TimelineClip, ts: number): Record<string, string> {
  const count = clip.thumb_count
  const index = clip.thumb_interval ? Math.min(count - 1, Math.max(0, Math.floor((ts - clip.start) / clip.thumb_interval))) : 0
  return {
    backgroundImage: `url(${media.sprite(clip.id)})`,
    backgroundSize: `${count * 100}% 100%`,
    backgroundPosition: `${count > 1 ? (index / (count - 1)) * 100 : 0}% 0`,
  }
}

const previewLeft = computed(() => {
  if (!hover.value) return 0
  const half = PREVIEW_WIDTH / 2 + 8
  return Math.min(Math.max(hover.value.clientX, half), window.innerWidth - half)
})

function setZoom(next: number, anchorClientX?: number) {
  const element = scroller.value
  if (!element) return
  const clamped = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next))
  const rect = element.getBoundingClientRect()
  const anchorOffset = anchorClientX !== undefined ? anchorClientX - rect.left : rect.width / 2
  const anchorTs =
    anchorClientX === undefined && props.playhead !== null && isVisible(props.playhead)
      ? props.playhead
      : tsAt(element.scrollLeft + anchorOffset)
  zoom.value = clamped
  nextTick(() => {
    element.scrollLeft = xOf(anchorTs) - anchorOffset
    scrollLeft.value = element.scrollLeft
  })
}

function isVisible(ts: number): boolean {
  const x = xOf(ts)
  return x >= scrollLeft.value && x <= scrollLeft.value + viewportWidth.value
}

function onWheel(event: WheelEvent) {
  if (!event.ctrlKey && !event.metaKey) return
  event.preventDefault()
  setZoom(zoom.value * (event.deltaY < 0 ? 1.25 : 0.8), event.clientX)
}

watch(
  () => props.playhead,
  (ts) => {
    const element = scroller.value
    if (ts === null || !element || zoom.value === 1 || isVisible(ts)) return
    element.scrollLeft = xOf(ts) - viewportWidth.value / 2
  },
)

watch(
  () => props.data.date,
  () => {
    zoom.value = 1
    hover.value = null
  },
)

onMounted(() => {
  if (!scroller.value) return
  resizeObserver = new ResizeObserver(([entry]) => (viewportWidth.value = Math.max(200, entry.contentRect.width)))
  resizeObserver.observe(scroller.value)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<template>
  <div class="card overflow-hidden p-0">
    <div class="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2">
      <span class="text-sm font-medium">Timeline</span>
      <span class="text-xs text-muted">{{ totalClips }} clips · {{ data.timezone }}</span>
      <div class="ml-auto flex items-center gap-1">
        <span class="hidden text-xs text-muted sm:inline">Ctrl + scroll to zoom</span>
        <button class="btn btn-ghost px-2" title="Zoom out" :disabled="zoom <= MIN_ZOOM" @click="setZoom(zoom / 2)">
          <AppIcon name="zoom-out" />
        </button>
        <span class="w-10 text-center text-xs tabular-nums">{{ zoom.toFixed(zoom < 10 ? 1 : 0) }}×</span>
        <button class="btn btn-ghost px-2" title="Zoom in" :disabled="zoom >= MAX_ZOOM" @click="setZoom(zoom * 2)">
          <AppIcon name="zoom-in" />
        </button>
        <button class="btn btn-ghost text-xs" :disabled="zoom === 1" @click="setZoom(1)">Fit</button>
      </div>
    </div>

    <div v-if="!data.lanes.length" class="px-4 py-10 text-center text-sm text-muted">
      No cameras match the current filter.
    </div>

    <div v-else class="flex">
      <div class="w-28 shrink-0 border-r border-line sm:w-40">
        <div class="h-7 border-b border-line" />
        <div
          v-for="lane in data.lanes"
          :key="lane.camera_id ?? 'unassigned'"
          class="flex h-12 items-center gap-2 border-b border-line px-3 text-sm last:border-b-0"
          :title="lane.name"
        >
          <span class="h-2.5 w-2.5 shrink-0 rounded-full" :style="{ background: lane.color }" />
          <span class="truncate">{{ lane.name }}</span>
        </div>
      </div>

      <div
        ref="scroller"
        class="relative min-w-0 flex-1 overflow-x-auto overflow-y-hidden"
        @scroll.passive="scrollLeft = ($event.target as HTMLElement).scrollLeft"
        @wheel="onWheel"
      >
        <div class="relative" :style="{ width: `${trackWidth}px` }">
          <div class="relative h-7 border-b border-line text-[11px] text-muted select-none">
            <div
              v-for="tick in ticks"
              :key="tick.ts"
              class="absolute top-0 bottom-0 border-l"
              :class="tick.major ? 'border-line' : 'border-line/50'"
              :style="{ left: `${tick.x}px` }"
            >
              <span class="ml-1 leading-7 whitespace-nowrap">{{ tick.label }}</span>
            </div>
          </div>

          <div
            v-for="lane in data.lanes"
            :key="lane.camera_id ?? 'unassigned'"
            class="relative h-12 cursor-pointer border-b border-line last:border-b-0"
            @mousemove="onMove(lane, $event)"
            @mouseleave="hover = null"
            @click="onClick(lane, $event)"
          >
            <div
              v-for="tick in ticks"
              v-show="tick.major"
              :key="tick.ts"
              class="pointer-events-none absolute top-0 bottom-0 border-l border-line/40"
              :style="{ left: `${tick.x}px` }"
            />

            <template v-if="!showClips">
              <div
                v-for="span in lane.spans"
                :key="span.start"
                class="pointer-events-none absolute top-2.5 bottom-2.5 rounded-sm opacity-80"
                :style="{
                  left: `${xOf(span.start)}px`,
                  width: `${Math.max(2, (span.end - span.start) * pxPerSec)}px`,
                  background: lane.color,
                }"
              />
            </template>

            <template v-else>
              <div
                v-for="clip in visibleClips(lane)"
                :key="clip.id"
                class="pointer-events-none absolute top-1.5 bottom-1.5 overflow-hidden rounded-sm border-r border-black/40 bg-cover bg-center"
                :class="clip.id === currentClipId ? 'ring-2 ring-white' : ''"
                :style="{
                  left: `${xOf(clip.start)}px`,
                  width: `${Math.max(2, (clip.end - clip.start) * pxPerSec)}px`,
                  backgroundColor: lane.color,
                  backgroundImage:
                    showThumbnails && clip.thumb_ready && (clip.end - clip.start) * pxPerSec >= INLINE_THUMB_WIDTH
                      ? `url(${media.poster(clip.id)})`
                      : undefined,
                }"
              />
            </template>
          </div>

          <div
            v-if="hover"
            class="pointer-events-none absolute top-7 bottom-0 w-px bg-fg/60"
            :style="{ left: `${hover.x}px` }"
          />
          <div
            v-if="playhead !== null && playhead >= data.day_start && playhead <= data.day_end"
            class="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-danger"
            :style="{ left: `${xOf(playhead)}px` }"
          >
            <span class="absolute -top-0 -left-1.5 h-3 w-3.5 rounded-b bg-danger" />
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="hover"
        class="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-full rounded-md bg-panel p-1.5 shadow-xl ring-1 ring-line"
        :style="{ left: `${previewLeft}px`, top: `${hover.top - 6}px`, width: `${PREVIEW_WIDTH}px` }"
      >
        <template v-if="hover.clip && showThumbnails">
          <div
            v-if="hover.clip.thumb_ready && hover.clip.thumb_count > 0"
            class="aspect-video w-full rounded bg-black bg-no-repeat"
            :style="spriteStyle(hover.clip, hover.ts)"
          />
          <img
            v-else-if="hover.clip.thumb_ready"
            :src="media.poster(hover.clip.id)"
            alt=""
            class="aspect-video w-full rounded bg-black object-cover"
          />
          <div v-else class="flex aspect-video w-full items-center justify-center rounded bg-black text-xs text-muted">
            Preview not generated yet
          </div>
        </template>
        <div class="flex items-center justify-between px-1 pt-1 text-xs">
          <span class="tabular-nums">{{ formatClock(hover.ts, data.timezone, hour12, true) }}</span>
          <span class="truncate pl-2 text-muted">{{ hover.clip ? hover.lane.name : 'No recording' }}</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>
