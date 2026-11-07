const formatterCache = new Map<string, Intl.DateTimeFormat>()

function formatter(key: string, options: Intl.DateTimeFormatOptions, locale?: string): Intl.DateTimeFormat {
  let cached = formatterCache.get(key)
  if (!cached) {
    cached = new Intl.DateTimeFormat(locale, options)
    formatterCache.set(key, cached)
  }
  return cached
}

export function isoDateIn(timestamp: number, timeZone: string): string {
  return formatter(`iso:${timeZone}`, { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }, 'en-CA').format(
    new Date(timestamp * 1000),
  )
}

export function todayIn(timeZone: string): string {
  return isoDateIn(Date.now() / 1000, timeZone)
}

export function shiftDate(date: string, days: number): string {
  const value = new Date(`${date}T00:00:00Z`)
  value.setUTCDate(value.getUTCDate() + days)
  return value.toISOString().slice(0, 10)
}

export function formatClock(timestamp: number, timeZone: string, hour12: boolean, seconds = false): string {
  const key = `clock:${timeZone}:${hour12}:${seconds}`
  return formatter(key, {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    second: seconds ? '2-digit' : undefined,
    hourCycle: hour12 ? 'h12' : 'h23',
  }).format(new Date(timestamp * 1000))
}

export function formatDateLong(date: string): string {
  return formatter('long', { timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(
    new Date(`${date}T00:00:00Z`),
  )
}

export function formatMonth(year: number, month: number): string {
  return formatter('month', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(
    new Date(Date.UTC(year, month - 1, 1)),
  )
}

export function weekdayLabels(firstDay: 0 | 1): string[] {
  const format = formatter('weekday', { timeZone: 'UTC', weekday: 'short' })
  return Array.from({ length: 7 }, (_, index) => format.format(new Date(Date.UTC(2023, 0, 1 + firstDay + index))))
}

export interface MonthCell {
  date: string
  day: number
  inMonth: boolean
}

export function monthMatrix(year: number, month: number, firstDay: 0 | 1): MonthCell[] {
  const first = new Date(Date.UTC(year, month - 1, 1))
  const offset = (first.getUTCDay() - firstDay + 7) % 7
  const start = new Date(first)
  start.setUTCDate(1 - offset)
  return Array.from({ length: 42 }, (_, index) => {
    const value = new Date(start)
    value.setUTCDate(start.getUTCDate() + index)
    return { date: value.toISOString().slice(0, 10), day: value.getUTCDate(), inMonth: value.getUTCMonth() === month - 1 }
  })
}

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours) return `${hours}h ${minutes}m`
  if (minutes) return `${minutes}m ${secs}s`
  return `${secs}s`
}

export function formatRelative(timestamp: number): string {
  const delta = timestamp - Date.now() / 1000
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  const abs = Math.abs(delta)
  if (abs < 60) return rtf.format(Math.round(delta), 'second')
  if (abs < 3600) return rtf.format(Math.round(delta / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(delta / 3600), 'hour')
  return rtf.format(Math.round(delta / 86400), 'day')
}
