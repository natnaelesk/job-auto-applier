export type Board = 'mik' | 'spark'

export type QueueItem = {
  board: Board
  page_id: string
  url: string
  name: string
  company: string
  role: string
  status: string | null
  apply_link: string | null
  source?: string | null
  location?: string | null
  remote?: boolean | null
  stack: string
  salary?: string | null
  why: string
  cv_path: string | null
  has_cv: boolean
  cover_letter: string | null
  applied_date?: string | null
  local_id?: string | number | null
  notes?: string | null
  client?: string | null
  platform?: string | null
  budget?: string | null
  package?: string | null
}

export type SessionState = {
  board: Board
  active: boolean
  index: number
  total: number
  current: QueueItem | null
  show_cover: boolean
}

export type LogEntry = {
  ts: string
  level: string
  message: string
}

export type Health = {
  ok: boolean
  notion: boolean
  ai: boolean
  ai_reason: string
  profile: boolean
  demo: boolean
  mik_ds: string
  spark_ds: string
}

export type BuildCvResult = {
  ok: boolean
  reason?: string
  done: number
  failed: number
  paths: string[]
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const detail =
      body && typeof body === 'object' && body !== null && 'detail' in body
        ? (body as { detail: unknown }).detail
        : res.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  // Never swallow a 200 with ok:false
  if (
    body &&
    typeof body === 'object' &&
    body !== null &&
    'ok' in body &&
    (body as { ok: unknown }).ok === false
  ) {
    const reason =
      'reason' in body && typeof (body as { reason: unknown }).reason === 'string'
        ? (body as { reason: string }).reason
        : 'error' in body && typeof (body as { error: unknown }).error === 'string'
          ? (body as { error: string }).error
          : 'Request failed (ok:false)'
    throw new Error(reason)
  }
  return body as T
}

export const api = {
  health: () => req<Health>('/api/health'),
  queue: (board: Board) =>
    req<{ board: Board; items: QueueItem[]; count: number }>(`/api/queue/${board}`),
  session: () => req<SessionState>('/api/session'),
  start: (board: Board, page_id?: string) =>
    req<SessionState>('/api/session/start', {
      method: 'POST',
      body: JSON.stringify({ board, page_id: page_id || null }),
    }),
  stop: () => req<SessionState>('/api/session/stop', { method: 'POST' }),
  next: () => req<SessionState>('/api/session/next', { method: 'POST' }),
  toggleCover: () =>
    req<SessionState>('/api/session/toggle-cover', { method: 'POST' }),
  openLink: () =>
    req<{ ok: boolean; url: string | null; error?: string | null }>(
      '/api/session/open-link',
      { method: 'POST' },
    ),
  mark: (board: Board, page_id: string, status: 'Applied' | 'Closed' | 'Later', notes?: string) =>
    req<{ ok: boolean; session: SessionState }>('/api/mark', {
      method: 'POST',
      body: JSON.stringify({ board, page_id, status, notes: notes || null }),
    }),
  cover: (board: Board, page_id: string, user_note = '') =>
    req<{ ok: boolean; path: string }>('/api/cover-letter', {
      method: 'POST',
      body: JSON.stringify({ board, page_id, user_note }),
    }),
  buildCv: (board: Board, page_id?: string) =>
    req<BuildCvResult>('/api/build-cv', {
      method: 'POST',
      body: JSON.stringify({ board, page_id: page_id || null, limit: 20 }),
    }),
  logs: () => req<{ entries: LogEntry[] }>('/api/logs'),
  clearLogs: () => req<{ ok: boolean }>('/api/logs/clear', { method: 'POST' }),
  fileUrl: (path: string) => `/api/file?path=${encodeURIComponent(path)}`,
}

export async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // Fallback for non-secure contexts / denied clipboard
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
    } finally {
      document.body.removeChild(ta)
    }
  }
}
