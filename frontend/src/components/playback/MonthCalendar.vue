<script setup lang="ts">
import { computed } from 'vue'
import type { CalendarDay } from '../../api/types'
import { useCatalogStore } from '../../stores/catalog'
import { formatDuration, formatMonth, monthMatrix, weekdayLabels } from '../../utils/time'
import AppIcon from '../ui/AppIcon.vue'

const props = defineProps<{
  year: number
  month: number
  selected: string
  today: string
  days: CalendarDay[]
  firstDayOfWeek: 0 | 1
  loading?: boolean
}>()
const emit = defineEmits<{ select: [date: string]; navigate: [year: number, month: number] }>()
const catalog = useCatalogStore()

const cells = computed(() => monthMatrix(props.year, props.month, props.firstDayOfWeek))
const weekdays = computed(() => weekdayLabels(props.firstDayOfWeek))
const byDate = computed(() => new Map(props.days.map((day) => [day.date, day])))
const maxDuration = computed(() => Math.max(1, ...props.days.map((day) => day.duration)))

function shift(delta: number) {
  let month = props.month + delta
  let year = props.year
  if (month < 1) {
    month = 12
    year -= 1
  } else if (month > 12) {
    month = 1
    year += 1
  }
  emit('navigate', year, month)
}

function dayColors(day: CalendarDay | undefined): string[] {
  if (!day) return []
  return day.camera_ids.slice(0, 4).map((id) => (id === null ? '#6b7280' : catalog.cameraById.get(id)?.color ?? '#6b7280'))
}

function dayTitle(date: string, day: CalendarDay | undefined): string {
  return day ? `${date}: ${day.clips} clips, ${formatDuration(day.duration)} recorded` : `${date}: no recordings`
}
</script>

<template>
  <div class="card p-4">
    <div class="mb-3 flex items-center justify-between">
      <button class="btn btn-ghost px-2" title="Previous month" @click="shift(-1)"><AppIcon name="chevron-left" /></button>
      <span class="text-sm font-medium" :class="{ 'animate-pulse': loading }">{{ formatMonth(year, month) }}</span>
      <button class="btn btn-ghost px-2" title="Next month" @click="shift(1)"><AppIcon name="chevron-right" /></button>
    </div>
    <div class="grid grid-cols-7 gap-1 text-center text-xs text-muted">
      <span v-for="weekday in weekdays" :key="weekday" class="py-1">{{ weekday }}</span>
    </div>
    <div class="grid grid-cols-7 gap-1">
      <button
        v-for="cell in cells"
        :key="cell.date"
        class="relative flex aspect-square flex-col items-center justify-center rounded text-sm transition-colors"
        :class="[
          cell.date === selected ? 'bg-accent text-white' : 'hover:bg-hover',
          !cell.inMonth && 'opacity-35',
          !byDate.has(cell.date) && cell.date !== selected && 'text-muted',
          cell.date === today && cell.date !== selected && 'font-bold text-accent ring-1 ring-accent/60',
        ]"
        :title="dayTitle(cell.date, byDate.get(cell.date))"
        @click="emit('select', cell.date)"
      >
        {{ cell.day }}
        <span v-if="byDate.has(cell.date)" class="absolute bottom-1 flex gap-0.5">
          <span
            v-for="(color, index) in dayColors(byDate.get(cell.date))"
            :key="index"
            class="h-1 w-1 rounded-full"
            :style="{ background: cell.date === selected ? '#fff' : color }"
          />
        </span>
        <span
          v-if="byDate.has(cell.date)"
          class="absolute inset-x-1 top-0.5 h-0.5 rounded bg-current opacity-30"
          :style="{ transform: `scaleX(${byDate.get(cell.date)!.duration / maxDuration})`, transformOrigin: 'left' }"
        />
      </button>
    </div>
  </div>
</template>
