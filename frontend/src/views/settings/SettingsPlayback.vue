<script setup lang="ts">
import SaveToolbar from '../../components/settings/SaveToolbar.vue'
import FieldSet from '../../components/ui/FieldSet.vue'
import FormRow from '../../components/ui/FormRow.vue'
import TagInput from '../../components/ui/TagInput.vue'
import ToggleSwitch from '../../components/ui/ToggleSwitch.vue'
import { useSettingsForm } from '../../composables/useSettingsForm'

const { draft, dirty, saving, error, savedAt, save, discard } = useSettingsForm(['playback', 'ffmpeg', 'thumbnails'])
const PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium']
</script>

<template>
  <SaveToolbar :dirty="dirty" :saving="saving" :error="error" :saved-at="savedAt" @save="save" @discard="discard" />
  <div v-if="draft" class="p-4 sm:p-6">
    <FieldSet legend="Playback">
      <FormRow
        label="Mode"
        input-id="playback-mode"
        help="Auto serves compatible MP4 directly, remuxes compatible MKV to MP4 and transcodes everything else to HLS."
      >
        <select id="playback-mode" v-model="draft.playback.mode" class="input w-56">
          <option value="auto">Auto (direct / remux / HLS)</option>
          <option value="transcode">Always transcode to HLS</option>
        </select>
      </FormRow>
      <FormRow label="Browser video codecs" help="Codecs the browser plays natively. Add 'hevc' if all your clients support H.265.">
        <TagInput v-model="draft.playback.direct_video_codecs" />
      </FormRow>
      <FormRow label="Browser audio codecs">
        <TagInput v-model="draft.playback.direct_audio_codecs" />
      </FormRow>
      <FormRow label="Cache size" input-id="cache-size" help="Remuxed MP4s and HLS segments are evicted least-recently-used first.">
        <div class="flex items-center gap-2">
          <input id="cache-size" v-model.number="draft.playback.cache_size_mb" type="number" min="64" class="input w-32" />
          <span class="text-sm text-muted">MB</span>
        </div>
      </FormRow>
    </FieldSet>

    <FieldSet legend="FFmpeg">
      <FormRow label="ffmpeg path" input-id="ffmpeg-path">
        <input id="ffmpeg-path" v-model="draft.ffmpeg.ffmpeg_path" class="input font-mono text-xs" />
      </FormRow>
      <FormRow label="ffprobe path" input-id="ffprobe-path">
        <input id="ffprobe-path" v-model="draft.ffmpeg.ffprobe_path" class="input font-mono text-xs" />
      </FormRow>
      <FormRow label="Hardware acceleration" input-id="hwaccel" help="VAAPI/QSV need /dev/dri passed to the container.">
        <select id="hwaccel" v-model="draft.ffmpeg.hwaccel" class="input w-56">
          <option value="none">None (libx264)</option>
          <option value="vaapi">VAAPI</option>
          <option value="qsv">Intel Quick Sync</option>
          <option value="nvenc">NVIDIA NVENC</option>
        </select>
      </FormRow>
      <FormRow v-if="draft.ffmpeg.hwaccel === 'vaapi'" label="VAAPI device" input-id="hw-device">
        <input id="hw-device" v-model="draft.ffmpeg.hwaccel_device" class="input font-mono text-xs" />
      </FormRow>
      <FormRow label="Encoder preset" input-id="preset">
        <select id="preset" v-model="draft.ffmpeg.video_preset" class="input w-56">
          <option v-for="preset in PRESETS" :key="preset" :value="preset">{{ preset }}</option>
        </select>
      </FormRow>
      <FormRow label="Quality (CRF / QP)" input-id="quality" help="Lower is better quality and bigger output. 23 is a sensible default.">
        <input id="quality" v-model.number="draft.ffmpeg.video_quality" type="number" min="0" max="51" class="input w-28" />
      </FormRow>
      <FormRow label="HLS segment length" input-id="hls-seg">
        <div class="flex items-center gap-2">
          <input id="hls-seg" v-model.number="draft.ffmpeg.hls_segment_seconds" type="number" min="1" max="30" class="input w-28" />
          <span class="text-sm text-muted">seconds</span>
        </div>
      </FormRow>
      <FormRow label="Extra input arguments" help="Inserted before -i, one token per entry.">
        <TagInput v-model="draft.ffmpeg.extra_input_args" placeholder="-fflags, +genpts" />
      </FormRow>
      <FormRow label="Extra output arguments">
        <TagInput v-model="draft.ffmpeg.extra_output_args" />
      </FormRow>
    </FieldSet>

    <FieldSet legend="Thumbnails">
      <FormRow label="Generate thumbnails">
        <ToggleSwitch v-model="draft.thumbnails.enabled" />
      </FormRow>
      <FormRow label="Sprite interval" input-id="thumb-interval" help="One hover frame every N seconds of video.">
        <div class="flex items-center gap-2">
          <input id="thumb-interval" v-model.number="draft.thumbnails.interval_seconds" type="number" min="1" class="input w-28" />
          <span class="text-sm text-muted">seconds</span>
        </div>
      </FormRow>
      <FormRow label="Max frames per clip" input-id="thumb-max">
        <input id="thumb-max" v-model.number="draft.thumbnails.max_per_clip" type="number" min="1" max="300" class="input w-28" />
      </FormRow>
      <FormRow label="Sprite frame width" input-id="sprite-width">
        <input id="sprite-width" v-model.number="draft.thumbnails.sprite_width" type="number" min="64" max="640" class="input w-28" />
      </FormRow>
      <FormRow label="Poster width" input-id="poster-width">
        <input id="poster-width" v-model.number="draft.thumbnails.poster_width" type="number" min="64" max="1280" class="input w-28" />
      </FormRow>
      <FormRow label="Parallel jobs" input-id="thumb-jobs">
        <input id="thumb-jobs" v-model.number="draft.thumbnails.concurrency" type="number" min="1" max="8" class="input w-28" />
      </FormRow>
    </FieldSet>
  </div>
</template>
