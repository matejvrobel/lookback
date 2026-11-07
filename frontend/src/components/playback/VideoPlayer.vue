<script setup lang="ts">
import type Hls from 'hls.js'
import { computed, onBeforeUnmount, onMounted, ref, watch, type ComponentPublicInstance } from 'vue'
import { api, errorMessage, media } from '../../api/client'
import type { PlayableClip, PlaybackInfo, PlaybackRate, PlayRequest } from '../../api/types'
import { formatClock, formatDuration } from '../../utils/time'
import AppIcon from '../ui/AppIcon.vue'
import ToggleSwitch from '../ui/ToggleSwitch.vue'

const props = defineProps<{
  request: PlayRequest | null
  timeZone: string
  hour12: boolean
  resolveNext: (clip: PlayableClip) => Promise<PlayableClip | null>
  resolvePrevious: (clip: PlayableClip) => Promise<PlayableClip | null>
}>()
const emit = defineEmits<{ 'clip-change': [clip: PlayableClip]; time: [timestamp: number] }>()
const autoplay = defineModel<boolean>('autoplay', { required: true })
const rate = defineModel<PlaybackRate>('rate', { required: true })

const RATES: PlaybackRate[] = [1, 2, 4, 8]
const PRELOAD_WALL_SECONDS = 20
const GAP_NOTICE_SECONDS = 5
const METADATA_TIMEOUT_MS = 60000

interface Slot {
  clip: PlayableClip | null
  hls: Hls | null
  method: PlaybackInfo['method'] | null
  ready: boolean
}

const videoEls: (HTMLVideoElement | null)[] = [null, null]
const slots: Slot[] = [
  { clip: null, hls: null, method: null, ready: false },
  { clip: null, hls: null, method: null, ready: false },
]
const active = ref(0)
const current = ref<PlayableClip | null>(null)
const method = ref<PlaybackInfo['method'] | null>(null)
const status = ref<'idle' | 'loading' | 'playing' | 'paused' | 'ended' | 'error'>('idle')
const message = ref<string | null>(null)
const clock = ref<number | null>(null)
let loadToken = 0
let preloadFor: number | null = null
let nextClip: PlayableClip | null = null

const clockLabel = computed(() => (clock.value === null ? '--:--:--' : formatClock(clock.value, props.timeZone, props.hour12, true)))

function setVideo(index: number, element: Element | ComponentPublicInstance | null) {
  videoEls[index] = element as HTMLVideoElement | null
}

function videoEl(index: number): HTMLVideoElement {
  const element = videoEls[index]
  if (!element) throw new Error('Video element is not mounted')
  return element
}

function applyRate(video: HTMLVideoElement) {
  video.defaultPlaybackRate = rate.value
  video.playbackRate = rate.value
}

function release(index: number) {
  const slot = slots[index]
  slot.hls?.destroy()
  Object.assign(slot, { clip: null, hls: null, method: null, ready: false })
  const video = videoEls[index]
  if (video) {
    video.pause()
    video.removeAttribute('src')
    video.load()
  }
}

function waitForMetadata(video: HTMLVideoElement): Promise<void> {
  if (video.readyState >= HTMLMediaElement.HAVE_METADATA) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => finish(new Error('Timed out while loading the recording')), METADATA_TIMEOUT_MS)
    const onLoaded = () => finish()
    const onError = () => finish(new Error('The browser could not load this recording'))
    function finish(error?: Error) {
      window.clearTimeout(timer)
      video.removeEventListener('loadedmetadata', onLoaded)
      video.removeEventListener('error', onError)
      if (error) reject(error)
      else resolve()
    }
    video.addEventListener('loadedmetadata', onLoaded)
    video.addEventListener('error', onError)
  })
}

async function attach(index: number, clip: PlayableClip): Promise<boolean> {
  release(index)
  const slot = slots[index]
  const video = videoEl(index)
  slot.clip = clip

  const info = await api<PlaybackInfo>(`/recordings/${clip.id}/playback`)
  if (slot.clip !== clip) return false
  slot.method = info.method

  let fatal: Promise<never> | null = null
  const HlsPlayer = info.method === 'hls' ? (await import('hls.js')).default : null
  if (slot.clip !== clip) return false
  if (HlsPlayer && !HlsPlayer.isSupported() && !video.canPlayType('application/vnd.apple.mpegurl')) {
    throw new Error('HLS playback is not supported by this browser')
  }
  if (HlsPlayer?.isSupported()) {
    const hls = new HlsPlayer({ startPosition: 0, maxBufferLength: 30 })
    slot.hls = hls
    fatal = new Promise<never>((_, reject) => {
      hls.on(HlsPlayer.Events.ERROR, (_event, data) => {
        if (data.fatal) reject(new Error(`HLS error: ${data.details}`))
      })
    })
    fatal.catch(() => undefined)
    hls.loadSource(info.url)
    hls.attachMedia(video)
  } else {
    video.src = info.url
  }
  applyRate(video)

  await (fatal ? Promise.race([waitForMetadata(video), fatal]) : waitForMetadata(video))
  if (slot.clip !== clip) return false
  slot.ready = true
  return true
}

function swap() {
  const previous = active.value
  const outgoing = videoEl(previous)
  const incoming = videoEl(1 - previous)
  incoming.muted = outgoing.muted
  incoming.volume = outgoing.volume
  active.value = 1 - previous
  release(previous)
}

async function play(clip: PlayableClip, offset = 0, announce = false) {
  const token = ++loadToken
  message.value = null
  preloadFor = null
  nextClip = null
  const standby = 1 - active.value

  try {
    const activeSlot = slots[active.value]
    if (activeSlot.clip?.id === clip.id && activeSlot.ready) {
      release(standby)
    } else if (slots[standby].clip?.id === clip.id && slots[standby].ready) {
      swap()
    } else {
      status.value = 'loading'
      release(standby)
      if (!(await attach(active.value, clip)) || token !== loadToken) return
    }

    const video = videoEl(active.value)
    current.value = clip
    method.value = slots[active.value].method
    clock.value = clip.start + offset
    if (offset > 0) video.currentTime = Number.isFinite(video.duration) ? Math.min(offset, video.duration - 0.25) : offset
    applyRate(video)
    if (announce) emit('clip-change', clip)
    await video.play()
  } catch (error) {
    if (token !== loadToken) return
    if (error instanceof DOMException && error.name === 'NotAllowedError') {
      status.value = 'paused'
      message.value = 'Autoplay was blocked by the browser, press play to start.'
      return
    }
    status.value = 'error'
    message.value = errorMessage(error)
  }
}

async function preloadNext(clip: PlayableClip) {
  const token = loadToken
  try {
    const next = await props.resolveNext(clip)
    if (!next || token !== loadToken) return
    nextClip = next
    const standby = 1 - active.value
    if (await attach(standby, next)) videoEl(standby).currentTime = 0
  } catch {
    if (token === loadToken) release(1 - active.value)
  }
}

function onTimeUpdate(index: number) {
  if (index !== active.value || !current.value) return
  const video = videoEl(index)
  clock.value = current.value.start + video.currentTime
  emit('time', clock.value)

  if (!autoplay.value || preloadFor === current.value.id) return
  const remaining = (video.duration - video.currentTime) / (video.playbackRate || 1)
  if (Number.isFinite(remaining) && remaining < PRELOAD_WALL_SECONDS) {
    preloadFor = current.value.id
    preloadNext(current.value)
  }
}

async function onEnded(index: number) {
  if (index !== active.value || !current.value) return
  status.value = 'ended'
  if (!autoplay.value) return

  const finished = current.value
  const next = nextClip ?? (await props.resolveNext(finished).catch(() => null))
  if (!next) {
    message.value = 'End of recordings for this camera.'
    return
  }
  const gap = next.start - finished.end
  await play(next, 0, true)
  if (gap > GAP_NOTICE_SECONDS) message.value = `Skipped ${formatDuration(gap)} without recordings.`
}

function onPlayState(index: number, state: 'playing' | 'paused') {
  if (index === active.value && current.value) status.value = state
}

function onVideoError(index: number) {
  if (index !== active.value || !current.value || status.value === 'loading') return
  status.value = 'error'
  message.value = 'Playback failed. Check the FFmpeg settings or try transcoding.'
}

async function step(direction: 1 | -1) {
  if (!current.value) return
  const resolver = direction > 0 ? props.resolveNext : props.resolvePrevious
  const target = await resolver(current.value).catch(() => null)
  if (target) await play(target, 0, true)
  else message.value = direction > 0 ? 'No later recording.' : 'No earlier recording.'
}

function togglePlay() {
  if (!current.value) return
  const video = videoEl(active.value)
  if (video.paused) video.play().catch((error) => (message.value = errorMessage(error)))
  else video.pause()
}

watch(rate, () => videoEls.forEach((video) => video && applyRate(video)))

watch(autoplay, (enabled) => {
  if (!enabled) {
    nextClip = null
    preloadFor = null
    release(1 - active.value)
  }
})

watch(
  () => props.request?.token,
  () => {
    if (props.request) play(props.request.clip, props.request.offset)
  },
)

onMounted(() => {
  if (props.request) play(props.request.clip, props.request.offset)
})

onBeforeUnmount(() => {
  loadToken += 1
  release(0)
  release(1)
})
</script>

<template>
  <div class="card overflow-hidden p-0">
    <div class="relative aspect-video w-full bg-black">
      <video
        v-for="index in [0, 1]"
        :key="index"
        :ref="(element) => setVideo(index, element)"
        class="absolute inset-0 h-full w-full"
        :class="index === active ? 'visible' : 'invisible'"
        :controls="index === active && current !== null"
        preload="auto"
        playsinline
        @timeupdate="onTimeUpdate(index)"
        @ended="onEnded(index)"
        @playing="onPlayState(index, 'playing')"
        @pause="onPlayState(index, 'paused')"
        @error="onVideoError(index)"
      />

      <div
        v-if="!current && status !== 'loading'"
        class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center text-sm text-zinc-400"
      >
        <AppIcon name="play" :size="40" />
        Pick a day, then click the timeline to start playback.
      </div>
      <div v-if="status === 'loading'" class="absolute inset-0 flex items-center justify-center bg-black/40">
        <span class="h-10 w-10 animate-spin rounded-full border-4 border-white/20 border-t-white" />
      </div>
      <div
        v-if="message"
        class="absolute top-3 left-1/2 max-w-[90%] -translate-x-1/2 rounded px-3 py-1.5 text-sm text-white shadow"
        :class="status === 'error' ? 'bg-danger/90' : 'bg-black/70'"
      >
        {{ message }}
      </div>
      <div
        v-if="current"
        class="pointer-events-none absolute top-3 left-3 rounded bg-black/60 px-2 py-1 font-mono text-sm text-white tabular-nums"
      >
        {{ clockLabel }}
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2">
      <div class="flex items-center gap-1">
        <button class="btn btn-ghost px-2" title="Previous clip" :disabled="!current" @click="step(-1)">
          <AppIcon name="skip-prev" />
        </button>
        <button class="btn btn-ghost px-2" :title="status === 'playing' ? 'Pause' : 'Play'" :disabled="!current" @click="togglePlay">
          <AppIcon :name="status === 'playing' ? 'pause' : 'play'" />
        </button>
        <button class="btn btn-ghost px-2" title="Next clip" :disabled="!current" @click="step(1)">
          <AppIcon name="skip-next" />
        </button>
      </div>

      <div class="inline-flex overflow-hidden rounded border border-line" role="group" aria-label="Playback speed">
        <button
          v-for="value in RATES"
          :key="value"
          class="px-2.5 py-1 text-sm tabular-nums transition-colors"
          :class="rate === value ? 'bg-accent text-white' : 'bg-canvas text-muted hover:text-fg'"
          @click="rate = value"
        >
          {{ value }}×
        </button>
      </div>

      <ToggleSwitch v-model="autoplay" label="Auto-play next" />

      <div class="ml-auto flex min-w-0 items-center gap-3 text-sm">
        <span v-if="current" class="truncate text-muted">{{ current.label }}</span>
        <span v-if="method" class="badge bg-raised uppercase">{{ method }}</span>
        <a v-if="current" :href="media.download(current.id)" class="btn btn-ghost px-2" title="Download clip">
          <AppIcon name="download" />
        </a>
      </div>
    </div>
  </div>
</template>
