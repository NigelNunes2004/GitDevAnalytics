import { useEffect, useState } from 'react'
import { api, type DeploymentItem, type Repository } from '../api'

type Props = {
  repos: Repository[]
  tokenConfigured: boolean
  selectedRepo: string
  onSelectRepo: (repo: string) => void
}

export function DeploymentsPage({
  repos,
  tokenConfigured,
  selectedRepo,
  onSelectRepo,
}: Props) {
  const [items, setItems] = useState<DeploymentItem[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function load(repo: string) {
    if (!repo || !tokenConfigured) return
    setBusy(true)
    setError('')
    try {
      setItems(await api.deployments(repo))
    } catch (err) {
      setItems([])
      setError(err instanceof Error ? err.message : 'Failed to load deployments')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!selectedRepo || !tokenConfigured) return
    let cancelled = false
    setBusy(true)
    setError('')
    api
      .deployments(selectedRepo)
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
  }, [selectedRepo, tokenConfigured])

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Deployments</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Recent GitHub Deployments API events (requires{' '}
          <code className="font-[var(--mono)]">repo_deployment</code>).
        </p>
      </header>
      <section className="gh-panel flex flex-wrap items-end gap-3 p-4">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Repository</span>
          <select
            className="gh-select min-w-56"
            value={selectedRepo}
            onChange={(e) => onSelectRepo(e.target.value)}
          >
            {repos.map((r) => (
              <option key={r.id} value={r.full_name}>
                {r.full_name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="gh-btn"
          disabled={busy || !selectedRepo}
          onClick={() => load(selectedRepo)}
        >
          Refresh
        </button>
      </section>
      {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}
      <section className="gh-panel p-4">
        {items.length === 0 ? (
          <p className="m-0 text-sm text-[var(--muted)]">No deployments found for this repo.</p>
        ) : (
          <ul className="m-0 list-none space-y-2 p-0">
            {items.map((d) => (
              <li
                key={d.id}
                className="rounded-md border border-[var(--line)] bg-[var(--bg)] px-3 py-3 text-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="m-0 font-semibold">{d.environment}</p>
                  <span className="font-[var(--mono)] text-xs uppercase">
                    {d.latest_state ?? 'unknown'}
                  </span>
                </div>
                <p className="mt-1 mb-0 text-[var(--muted)]">
                  {d.ref} · {d.sha.slice(0, 7)} · {d.task}
                  {d.created_at ? ` · ${new Date(d.created_at).toLocaleString()}` : ''}
                </p>
                {d.latest_description ? (
                  <p className="mt-1 mb-0 text-[var(--ink)]">{d.latest_description}</p>
                ) : null}
                {d.latest_url ? (
                  <a href={d.latest_url} target="_blank" rel="noreferrer" className="gh-link text-xs">
                    Open environment / logs
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
