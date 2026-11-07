<script setup lang="ts">
import SaveToolbar from '../../components/settings/SaveToolbar.vue'
import FieldSet from '../../components/ui/FieldSet.vue'
import FormRow from '../../components/ui/FormRow.vue'
import ToggleSwitch from '../../components/ui/ToggleSwitch.vue'
import { useSettingsForm } from '../../composables/useSettingsForm'

const { draft, dirty, saving, error, savedAt, save, discard } = useSettingsForm(['general', 'ui'])
const timezones = ['UTC', ...Intl.supportedValuesOf('timeZone').filter((zone) => zone !== 'UTC')]
const RATES = [1, 2, 4, 8] as const
</script>

<template>
  <SaveToolbar :dirty="dirty" :saving="saving" :error="error" :saved-at="savedAt" @save="save" @discard="discard" />
  <div v-if="draft" class="p-4 sm:p-6">
    <FieldSet legend="Host">
      <FormRow label="Instance name" input-id="instance-name" help="Shown in the header and browser tab.">
        <input id="instance-name" v-model="draft.general.instance_name" class="input" />
      </FormRow>
      <FormRow
        label="Timezone"
        input-id="timezone"
        help="Used to read timestamps in filenames and to split the calendar into days. Changing it re-indexes the library."
      >
        <select id="timezone" v-model="draft.general.timezone" class="input">
          <option v-for="zone in timezones" :key="zone" :value="zone">{{ zone }}</option>
        </select>
      </FormRow>
    </FieldSet>

    <FieldSet legend="User Interface">
      <FormRow label="Theme" input-id="theme">
        <select id="theme" v-model="draft.ui.theme" class="input w-48">
          <option value="dark">Dark</option>
          <option value="light">Light</option>
          <option value="system">Follow system</option>
        </select>
      </FormRow>
      <FormRow label="First day of week" input-id="first-day">
        <select id="first-day" v-model.number="draft.ui.first_day_of_week" class="input w-48">
          <option :value="1">Monday</option>
          <option :value="0">Sunday</option>
        </select>
      </FormRow>
      <FormRow label="Time format" input-id="time-format">
        <select id="time-format" v-model="draft.ui.time_format" class="input w-48">
          <option value="24h">24-hour (17:30)</option>
          <option value="12h">12-hour (5:30 PM)</option>
        </select>
      </FormRow>
    </FieldSet>

    <FieldSet legend="Player &amp; Timeline">
      <FormRow label="Default speed">
        <div class="inline-flex overflow-hidden rounded border border-line">
          <button
            v-for="rate in RATES"
            :key="rate"
            type="button"
            class="px-3 py-1.5 text-sm"
            :class="draft.ui.default_playback_rate === rate ? 'bg-accent text-white' : 'bg-canvas text-muted hover:text-fg'"
            @click="draft.ui.default_playback_rate = rate"
          >
            {{ rate }}×
          </button>
        </div>
      </FormRow>
      <FormRow label="Auto-play next clip" help="Default state of the player toggle.">
        <ToggleSwitch v-model="draft.ui.autoplay_next" />
      </FormRow>
      <FormRow
        label="Merge gaps up to"
        input-id="gap"
        help="Clips separated by less than this are drawn as one continuous block on the timeline."
      >
        <div class="flex items-center gap-2">
          <input id="gap" v-model.number="draft.ui.timeline_gap_merge_seconds" type="number" min="0" class="input w-28" />
          <span class="text-sm text-muted">seconds</span>
        </div>
      </FormRow>
      <FormRow label="Timeline thumbnails" help="Hover previews and inline posters when zoomed in.">
        <ToggleSwitch v-model="draft.ui.timeline_show_thumbnails" />
      </FormRow>
    </FieldSet>
  </div>
</template>
