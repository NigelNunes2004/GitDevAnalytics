import { useEffect, useState } from 'react'
import { api, type NotificationItem } from '../api'

type Props = {
  tokenConfigured: boolean
}

export function NotificationsPage({ tokenConfigured }: Props) {
  const [items, setItems] = useState<NotificationItem[]>([])
  const [includeRead, setIncludeRead] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function load(read: boolean) {
    if (!tokenConfigured) return
    setBusy(true)
    setError('')
    try {
      setItems(await api.notifications(read))
    } catch (err) {
      setItems([])
      setError(err instanceof Error ? err.message : 'Failed to load notifications')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!tokenConfigured) return
    let cancelled = false
    setBusy(true)
    setError('')
    api
      .notifications(includeRead)
      .then((rows) => {
        if (!cancelled) setItems(rows)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setItems([])
        setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setBusy(false)
      })
    return () => {
      cancelled = true
    }
  }, [tokenConfigured, includeRead])

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Notifications</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          GitHub notification inbox (requires <code className="font-[var(--mono)]">notifications</code>).
        </p>
      </header>
      <section className="gh-panel flex flex-wrap items-center gap-3 p-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeRead}
            onChange={(e) => setIncludeRead(e.target.checked)}
          />
          Include read
        </label>
        <button type="button" className="gh-btn" disabled={busy} onClick={() => load(includeRead)}>
          Refresh
        </button>
      </section>
      {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}
      <section className="gh-panel p-4">
        {items.length === 0 ? (
          <p className="m-0 text-sm text-[var(--muted)]">No notifications.</p>
        ) : (
          <ul className="m-0 list-none space-y-2 p-0">
            {items.map((n) => (
              <li
                key={n.id}
                className={`rounded-md border px-3 py-2 text-sm ${
                  n.unread
                    ? 'border-[rgba(56,139,253,0.4)] bg-[rgba(56,139,253,0.08)]'
                    : 'border-[var(--line)] bg-[var(--bg)]'
                }`}
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="m-0 font-medium">{n.title}</p>
                  <span className="text-xs text-[var(--muted)]">
                    {n.reason} · {n.type}
                  </span>
                </div>
                <p className="mt-1 mb-0 text-xs text-[var(--muted)]">
                  {n.repo ?? '—'}
                  {n.updated_at ? ` · ${new Date(n.updated_at).toLocaleString()}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
