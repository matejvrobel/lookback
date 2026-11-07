import type { SourceFilter } from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(formatDetail(detail) ?? `Request failed with status ${status}`)
  }
}

function formatDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item: { loc?: (string | number)[]; msg?: string }) => {
        const field = item.loc?.filter((part) => part !== 'body').join('.')
        return field ? `${field}: ${item.msg}` : item.msg
      })
      .join('; ')
  }
  return null
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

type QueryValue = string | number | boolean | null | undefined | (string | number)[]

export function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue
    if (Array.isArray(value)) value.forEach((item) => search.append(key, String(item)))
    else search.append(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function sourceParams(source: SourceFilter): Record<string, QueryValue> {
  if (source.kind === 'camera') return { camera_ids: [source.id] }
  if (source.kind === 'group') return { group_id: source.id }
  return {}
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? body)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const media = {
  poster: (id: number) => `/api/recordings/${id}/thumbnail.jpg`,
  sprite: (id: number) => `/api/recordings/${id}/sprite.jpg`,
  download: (id: number) => `/api/recordings/${id}/file?download=true`,
}
