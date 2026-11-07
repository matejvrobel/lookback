<script setup lang="ts">
import SaveToolbar from '../../components/settings/SaveToolbar.vue'
import FieldSet from '../../components/ui/FieldSet.vue'
import FormRow from '../../components/ui/FormRow.vue'
import ListEditor from '../../components/ui/ListEditor.vue'
import TagInput from '../../components/ui/TagInput.vue'
import ToggleSwitch from '../../components/ui/ToggleSwitch.vue'
import { useSettingsForm } from '../../composables/useSettingsForm'

const { draft, dirty, saving, error, savedAt, save, discard } = useSettingsForm(['library'])
</script>

<template>
  <SaveToolbar :dirty="dirty" :saving="saving" :error="error" :saved-at="savedAt" @save="save" @discard="discard" />
  <div v-if="draft" class="p-4 sm:p-6">
    <FieldSet legend="Root Folders">
      <FormRow
        label="Recording folders"
        help="Paths inside the container that are scanned recursively. Mount your NVR share read-only at /recordings."
      >
        <ListEditor v-model="draft.library.root_folders" placeholder="/recordings" />
      </FormRow>
    </FieldSet>

    <FieldSet legend="Files">
      <FormRow label="File extensions" help="Only files with these extensions are indexed.">
        <TagInput v-model="draft.library.extensions" placeholder=".mp4, .mkv" />
      </FormRow>
      <FormRow label="Ignore patterns" help="Glob patterns matched against the path relative to the root folder.">
        <ListEditor v-model="draft.library.ignore_patterns" placeholder="*/tmp/*" monospace />
      </FormRow>
      <FormRow
        label="Minimum file age"
        input-id="min-age"
        help="Files modified more recently are treated as still being written and skipped until the next scan."
      >
        <div class="flex items-center gap-2">
          <input id="min-age" v-model.number="draft.library.min_file_age_seconds" type="number" min="0" class="input w-32" />
          <span class="text-sm text-muted">seconds</span>
        </div>
      </FormRow>
      <FormRow
        label="Remove missing files"
        help="Delete database entries whose files disappeared. Roots that are offline or empty are never purged."
      >
        <ToggleSwitch v-model="draft.library.remove_missing" />
      </FormRow>
    </FieldSet>

    <FieldSet legend="Timestamp Parsing">
      <FormRow
        label="Filename patterns"
        help="Regular expressions tried in order against the filename, then the relative path. Use named groups Y, m, d, H, M, S or a single 'epoch' group. Changing them re-indexes the library."
      >
        <ListEditor v-model="draft.library.timestamp_patterns" placeholder="(?P<Y>\d{4})(?P<m>\d{2})…" monospace />
      </FormRow>
    </FieldSet>
  </div>
</template>
