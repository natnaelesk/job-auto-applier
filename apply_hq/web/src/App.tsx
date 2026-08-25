import { useCallback, useEffect, useState, type ReactNode } from 'react'
import {
  api,
  copyText,
  type Board,
  type Health,
  type LogEntry,
  type QueueItem,
  type SessionState,
} from './api'

function App() {
  const [board, setBoard] = useState<Board>('mik')
  const [items, setItems] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [session, setSession] = useState<SessionState | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const refreshQueue = useCallback(async (b: Board) => {
    setLoading(true)
    setError(null)
    try {
      const q = await api.queue(b)
      setItems(q.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshLogs = useCallback(async () => {
    try {
      const l = await api.logs()
      setLogs(l.entries)
    } catch {
      /* ignore */
    }
  }, [])

  const refreshSession = useCallback(async () => {
    try {
      setSession(await api.session())
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
    refreshQueue(board)
    refreshSession()
    refreshLogs()
    const t = setInterval(refreshLogs, 1500)
    return () => clearInterval(t)
  }, [board, refreshQueue, refreshLogs, refreshSession])

  const switchBoard = (b: Board) => {
    setBoard(b)
    setSelectedId(null)
    if (session?.active && session.board !== b) {
      api.stop().then(setSession).catch(() => undefined)
    }
  }

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
      await refreshLogs()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      await refreshLogs()
    } finally {
      setBusy(false)
    }
  }

  const onStartApplying = () =>
    run(async () => {
      const s = await api.start(board, selectedId || undefined)
      setSession(s)
      await refreshQueue(board)
    })

  const onBuildCv = () =>
    run(async () => {
      await api.buildCv(board, selectedId || undefined)
      await refreshQueue(board)
      await refreshSession()
    })

  const current = session?.active && session.board === board ? session.current : null

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col px-4 py-5 sm:px-6">
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-[0.18em] text-[var(--ink-dim)] uppercase">
            Natnael · manual apply
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--ink)]">
            Apply HQ
          </h1>
        </div>
        <div className="mono text-right text-[11px] text-[var(--ink-dim)]">
          {health ? (
            <>
              <div>Notion {health.notion ? 'ok' : 'missing token'}</div>
              <div title={health.ai_reason}>
                AI {health.ai ? 'ready' : 'stub'} · profile {health.profile ? 'ok' : 'missing'}
              </div>
            </>
          ) : (
            <div>connecting…</div>
          )}
        </div>
      </header>

      <div
        className="mb-4 inline-flex w-fit rounded-lg border border-[var(--line)] bg-[var(--surface)] p-1 shadow-[var(--shadow)]"
        role="tablist"
      >
        <TabButton active={board === 'mik'} onClick={() => switchBoard('mik')} tone="mik">
          Mik
        </TabButton>
        <TabButton active={board === 'spark'} onClick={() => switchBoard('spark')} tone="spark">
          Spark
        </TabButton>
      </div>

      <section className="mb-3 overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow)]">
        <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-2.5">
          <h2 className="text-sm font-semibold">
            Queue · Status Ready
            <span className="ml-2 font-normal text-[var(--ink-dim)]">
              {loading ? 'loading…' : `${items.length}`}
            </span>
          </h2>
          <button
            type="button"
            className="text-xs font-medium text-[var(--ink-dim)] hover:text-[var(--ink)]"
            onClick={() => refreshQueue(board)}
            disabled={busy}
          >
            Refresh
          </button>
        </div>
        <QueueTable
          board={board}
          items={items}
          selectedId={selectedId}
          currentId={current?.page_id}
          onSelect={setSelectedId}
        />
      </section>

      <div className="mb-3 flex flex-wrap gap-2">
        <PrimaryButton onClick={onStartApplying} disabled={busy || items.length === 0}>
          Start applying
        </PrimaryButton>
        <SecondaryButton onClick={onBuildCv} disabled={busy}>
          Build CV
        </SecondaryButton>
        {session?.active && session.board === board && (
          <SecondaryButton
            onClick={() => run(async () => setSession(await api.stop()))}
            disabled={busy}
          >
            Stop
          </SecondaryButton>
        )}
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}

      {current && session?.active && (
        <ApplyFront
          board={board}
          item={current}
          showCover={session.show_cover}
          index={session.index}
          total={session.total}
          busy={busy}
          run={run}
          onSession={setSession}
          onQueueRefresh={() => refreshQueue(board)}
        />
      )}

      <section className="mt-auto flex min-h-[180px] flex-1 flex-col overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--log-bg)] shadow-[var(--shadow)]">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
          <h2 className="text-xs font-semibold tracking-wide text-white/70 uppercase">Logs</h2>
          <button
            type="button"
            className="text-[11px] text-white/50 hover:text-white/80"
            onClick={() => run(async () => { await api.clearLogs(); setLogs([]) })}
          >
            Clear
          </button>
        </div>
        <div className="mono flex-1 overflow-auto px-4 py-3 text-[12px] leading-5 text-[var(--log-fg)]">
          {logs.length === 0 ? (
            <div className="text-white/40">No logs yet.</div>
          ) : (
            logs.map((e, i) => (
              <div key={`${e.ts}-${i}`} className={e.level === 'error' ? 'text-red-300' : e.level === 'warn' ? 'text-amber-200' : ''}>
                <span className="text-white/35">{e.ts.slice(11, 19)}</span> {e.message}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function ApplyFront({
  board,
  item,
  showCover,
  index,
  total,
  busy,
  run,
  onSession,
  onQueueRefresh,
}: {
  board: Board
  item: QueueItem
  showCover: boolean
  index: number
  total: number
  busy: boolean
  run: (fn: () => Promise<void>) => Promise<void>
  onSession: (s: SessionState) => void
  onQueueRefresh: () => void
}) {
  const link = item.apply_link || ''
  const cv = item.cv_path || ''
  const cover = item.cover_letter || ''

  return (
    <section className="mb-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-[var(--shadow)]">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs text-[var(--ink-dim)]">
            Applying {index + 1} / {total}
          </p>
          <h3 className="text-lg font-semibold">
            {item.company || item.client || '—'} — {item.role || item.name}
          </h3>
          <p className="mt-1 max-w-2xl text-sm text-[var(--ink-dim)] line-clamp-2">
            {item.why || item.stack || '—'}
          </p>
        </div>
        <button
          type="button"
          className="text-xs font-medium text-[var(--ink-dim)] hover:text-[var(--ink)]"
          disabled={busy}
          onClick={() => run(async () => onSession(await api.next()))}
        >
          Next →
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <PrimaryButton
          disabled={busy || !link}
          onClick={() =>
            run(async () => {
              const r = await api.openLink()
              if (r.url) await copyText(r.url)
            })
          }
        >
          Open / copy link
        </PrimaryButton>
        <SecondaryButton
          disabled={busy}
          onClick={() =>
            run(async () => {
              await api.cover(board, item.page_id)
              onSession(await api.session())
              onQueueRefresh()
            })
          }
        >
          Create cover letter
        </SecondaryButton>
        <SecondaryButton
          disabled={busy || !cv}
          onClick={() =>
            run(async () => {
              await copyText(cv)
            })
          }
        >
          Copy CV path
        </SecondaryButton>
        <SecondaryButton
          disabled={busy || !cv}
          onClick={() => {
            if (!cv) return
            window.open(api.fileUrl(cv), '_blank')
          }}
        >
          Preview CV
        </SecondaryButton>
        {cover ? (
          <SecondaryButton
            disabled={busy}
            onClick={() => run(async () => onSession(await api.toggleCover()))}
          >
            {showCover ? 'Hide cover letter' : 'Show cover letter'}
          </SecondaryButton>
        ) : null}
      </div>

      {showCover && cover && (
        <div className="mt-3 rounded-lg border border-[var(--line)] bg-[var(--paper)] px-3 py-2 text-sm">
          <div className="mb-1 text-xs font-semibold tracking-wide text-[var(--ink-dim)] uppercase">
            Cover letter
          </div>
          <div className="mono break-all text-[12px]">{cover}</div>
          <button
            type="button"
            className="mt-2 text-xs font-medium underline"
            onClick={() => window.open(api.fileUrl(cover), '_blank')}
          >
            Open PDF
          </button>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--line)] pt-3">
        <StatusButton
          label="Applied"
          tone="ok"
          disabled={busy}
          onClick={() =>
            run(async () => {
              const r = await api.mark(board, item.page_id, 'Applied')
              onSession(r.session)
              onQueueRefresh()
            })
          }
        />
        <StatusButton
          label="Closed"
          tone="danger"
          disabled={busy}
          onClick={() =>
            run(async () => {
              const r = await api.mark(board, item.page_id, 'Closed')
              onSession(r.session)
              onQueueRefresh()
            })
          }
        />
        <StatusButton
          label="Later"
          tone="neutral"
          disabled={busy}
          onClick={() =>
            run(async () => {
              const r = await api.mark(board, item.page_id, 'Later')
              onSession(r.session)
              onQueueRefresh()
            })
          }
        />
      </div>
    </section>
  )
}

function QueueTable({
  board,
  items,
  selectedId,
  currentId,
  onSelect,
}: {
  board: Board
  items: QueueItem[]
  selectedId: string | null
  currentId?: string
  onSelect: (id: string) => void
}) {
  if (items.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-[var(--ink-dim)]">
        No Ready rows. Mark jobs Ready in Notion to fill this queue.
      </div>
    )
  }

  return (
    <div className="max-h-[280px] overflow-auto">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead className="sticky top-0 bg-[var(--paper-2)] text-[11px] tracking-wide text-[var(--ink-dim)] uppercase">
          <tr>
            <th className="px-3 py-2 font-semibold">Company</th>
            <th className="px-3 py-2 font-semibold">{board === 'mik' ? 'Role' : 'Project'}</th>
            <th className="px-3 py-2 font-semibold">{board === 'mik' ? 'Source' : 'Platform'}</th>
            <th className="px-3 py-2 font-semibold">CV</th>
            <th className="px-3 py-2 font-semibold">Stack</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => {
            const active = row.page_id === selectedId || row.page_id === currentId
            return (
              <tr
                key={row.page_id}
                className={`cursor-pointer border-t border-[var(--line)] hover:bg-[var(--paper)] ${
                  active ? 'bg-[var(--mik-soft)]/50' : ''
                }`}
                onClick={() => onSelect(row.page_id)}
              >
                <td className="px-3 py-2 font-medium">{row.company || row.client || '—'}</td>
                <td className="px-3 py-2 text-[var(--ink-dim)]">
                  {board === 'mik' ? row.role || row.name : row.name}
                </td>
                <td className="px-3 py-2 text-[var(--ink-dim)]">
                  {board === 'mik' ? row.source || '—' : row.platform || '—'}
                </td>
                <td className="px-3 py-2">
                  {row.has_cv ? (
                    <span className="text-[var(--ok)]">yes</span>
                  ) : (
                    <span className="text-[var(--ink-dim)]">no</span>
                  )}
                </td>
                <td className="max-w-[180px] truncate px-3 py-2 text-[var(--ink-dim)]">
                  {row.stack || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  tone,
  children,
}: {
  active: boolean
  onClick: () => void
  tone: 'mik' | 'spark'
  children: ReactNode
}) {
  const activeCls =
    tone === 'mik'
      ? 'bg-[var(--mik)] text-white'
      : 'bg-[var(--spark)] text-white'
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-md px-4 py-1.5 text-sm font-semibold transition ${
        active ? activeCls : 'text-[var(--ink-dim)] hover:text-[var(--ink)]'
      }`}
    >
      {children}
    </button>
  )
}

function PrimaryButton({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded-lg bg-[var(--ink)] px-4 py-2 text-sm font-semibold text-white hover:bg-black"
    >
      {children}
    </button>
  )
}

function SecondaryButton({
  children,
  onClick,
  disabled,
}: {
  children: ReactNode
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--ink)] hover:bg-[var(--paper)]"
    >
      {children}
    </button>
  )
}

function StatusButton({
  label,
  tone,
  onClick,
  disabled,
}: {
  label: string
  tone: 'ok' | 'danger' | 'neutral'
  onClick: () => void
  disabled?: boolean
}) {
  const cls =
    tone === 'ok'
      ? 'bg-[var(--ok)] text-white'
      : tone === 'danger'
        ? 'bg-[var(--danger)] text-white'
        : 'border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)]'
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-semibold ${cls}`}
    >
      {label}
    </button>
  )
}

export default App
