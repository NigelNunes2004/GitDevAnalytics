import { useEffect, useState } from 'react'
import { api, type CommitStatusSummary, type Repository } from '../api'

type Props = {
  repos: Repository[]
  tokenConfigured: boolean
  selectedRepo: string
  onSelectRepo: (repo: string) => void
}

export function StatusPage({ repos, tokenConfigured, selectedRepo, onSelectRepo }: Props) {
  const [data, setData] = useState<CommitStatusSummary | null>(null)
  const [ref, setRef] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function load(repo: string, branch?: string) {
    if (!repo || !tokenConfigured) return
    setBusy(true)
    setError('')
    try {
      const result = await api.commitStatus(repo, branch || undefined)
      setData(result)
      setRef(result.ref)
    } catch (err) {
      setData(null)
      setError(err instanceof Error ? err.message : 'Failed to load statuses')
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
      .commitStatus(selectedRepo)
      .then((result) => {
        if (cancelled) return
        setData(result)
        setRef(result.ref)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setData(null)
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
        <h1 className="m-0 text-2xl font-semibold">Commit status</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Tip commit message, +/- lines, and CI statuses (requires{' '}
          <code className="font-[var(--mono)]">repo</code> / contents +{' '}
          <code className="font-[var(--mono)]">repo:status</code>).
        </p>
      </header>
      {!tokenConfigured ? (
        <p className="text-sm text-[#d29922]">Configure a PAT first.</p>
      ) : null}
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
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Ref / branch</span>
          <input className="gh-input min-w-40" value={ref} onChange={(e) => setRef(e.target.value)} />
        </label>
        <button
          type="button"
          className="gh-btn gh-btn-primary"
          disabled={busy || !selectedRepo}
          onClick={() => load(selectedRepo, ref)}
        >
          Refresh
        </button>
      </section>
      {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}

      {data ? (
        <>
          <section className="gh-panel p-4">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <p className="m-0 text-sm">
                <span className="font-semibold uppercase">{data.state}</span> on{' '}
                <code className="font-[var(--mono)]">{data.ref}</code>
                {data.sha ? (
                  <>
                    {' '}
                    · <code className="font-[var(--mono)] text-xs">{data.sha.slice(0, 7)}</code>
                  </>
                ) : null}
              </p>
              <p className="m-0 font-[var(--mono)] text-sm">
                <span className="text-[#3fb950]">+{data.additions}</span>
                {' / '}
                <span className="text-[#f85149]">−{data.deletions}</span>
              </p>
            </div>
            <p className="mt-0 mb-1 text-base font-medium text-[var(--ink)]">
              {data.message ?? '(no message)'}
            </p>
            <p className="m-0 text-xs text-[var(--muted)]">
              {data.author ?? 'unknown author'}
              {data.html_url ? (
                <>
                  {' · '}
                  <a href={data.html_url} target="_blank" rel="noreferrer" className="gh-link">
                    View on GitHub
                  </a>
                </>
              ) : null}
            </p>
          </section>

          <section className="gh-panel p-4">
            <h2 className="mt-0 mb-3 border-b border-[var(--line)] pb-2 text-sm font-semibold">
              Recent commits
            </h2>
            {data.recent_commits.length === 0 ? (
              <p className="m-0 text-sm text-[var(--muted)]">No commits found on this ref.</p>
            ) : (
              <ul className="m-0 list-none space-y-2 p-0">
                {data.recent_commits.map((c) => (
                  <li
                    key={c.sha}
                    className="rounded-md border border-[var(--line)] bg-[var(--bg)] px-3 py-2 text-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="m-0 font-medium">{c.message}</p>
                        <p className="mt-1 mb-0 text-xs text-[var(--muted)]">
                          <code className="font-[var(--mono)]">{c.sha.slice(0, 7)}</code>
                          {c.author ? ` · ${c.author}` : ''}
                          {c.committed_at
                            ? ` · ${new Date(c.committed_at).toLocaleString()}`
                            : ''}
                          {c.html_url ? (
                            <>
                              {' · '}
                              <a
                                href={c.html_url}
                                target="_blank"
                                rel="noreferrer"
                                className="gh-link"
                              >
                                GitHub
                              </a>
                            </>
                          ) : null}
                        </p>
                      </div>
                      <p className="m-0 shrink-0 font-[var(--mono)] text-xs">
                        <span className="text-[#3fb950]">+{c.additions}</span>
                        {' '}
                        <span className="text-[#f85149]">−{c.deletions}</span>
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="gh-panel p-4">
            <h2 className="mt-0 mb-3 border-b border-[var(--line)] pb-2 text-sm font-semibold">
              CI / external statuses ({data.total_count})
            </h2>
            {data.statuses.length === 0 ? (
              <p className="m-0 text-sm text-[var(--muted)]">
                No external commit statuses on this ref.
              </p>
            ) : (
              <ul className="m-0 list-none space-y-2 p-0">
                {data.statuses.map((s) => (
                  <li
                    key={s.context}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--line)] bg-[var(--bg)] px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="m-0 font-medium">{s.context}</p>
                      <p className="m-0 text-[var(--muted)]">{s.description ?? '—'}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-[var(--mono)] text-xs uppercase">{s.state}</span>
                      {s.target_url ? (
                        <a
                          href={s.target_url}
                          target="_blank"
                          rel="noreferrer"
                          className="gh-link text-xs"
                        >
                          Details
                        </a>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </div>
  )
}
