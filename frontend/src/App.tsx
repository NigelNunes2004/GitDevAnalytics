import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  api,
  type CommitPoint,
  type Contributor,
  type PRTurnaround,
  type Repository,
} from './api'

function App() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string>('')
  const [repoInput, setRepoInput] = useState('fastapi/fastapi')
  const [period, setPeriod] = useState<'day' | 'week'>('day')
  const [commits, setCommits] = useState<CommitPoint[]>([])
  const [contributors, setContributors] = useState<Contributor[]>([])
  const [turnaround, setTurnaround] = useState<PRTurnaround[]>([])
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [busy, setBusy] = useState(false)

  const refreshRepos = useCallback(async () => {
    const list = await api.listRepos()
    setRepos(list)
    setSelectedRepo((current) => current || (list[0]?.full_name ?? ''))
  }, [])

  const refreshStats = useCallback(async (repo: string, commitPeriod: 'day' | 'week') => {
    const filter = repo || undefined
    const [commitData, contributorData, prData] = await Promise.all([
      api.commits(filter, commitPeriod),
      api.contributors(filter),
      api.prTurnaround(filter),
    ])
    setCommits(commitData)
    setContributors(contributorData)
    setTurnaround(prData)
  }, [])

  useEffect(() => {
    refreshRepos().catch((err: Error) => setError(err.message))
  }, [refreshRepos])

  useEffect(() => {
    refreshStats(selectedRepo, period).catch((err: Error) => setError(err.message))
  }, [selectedRepo, period, refreshStats, repos.length])

  async function handleTrack() {
    setBusy(true)
    setError('')
    setStatus('')
    try {
      const names = repoInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      await api.trackRepos(names)
      await refreshRepos()
      setSelectedRepo(names[0])
      setStatus(`Tracking ${names.join(', ')}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to track repos')
    } finally {
      setBusy(false)
    }
  }

  async function handleSync() {
    setBusy(true)
    setError('')
    setStatus('Syncing from GitHub…')
    try {
      const result = await api.syncAll()
      const summary = result.results
        .map(
          (r) =>
            `${r.repo}: ${r.commits_upserted} commits, ${r.pull_requests_upserted} PRs`,
        )
        .join(' · ')
      setStatus(summary || 'No tracked repos to sync')
      await refreshStats(selectedRepo, period)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed')
      setStatus('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-8 border-b border-[var(--line)] pb-6">
        <p className="mb-1 font-[var(--mono)] text-xs tracking-[0.14em] text-[var(--muted)] uppercase">
          DevOps portfolio tool
        </p>
        <h1 className="m-0 text-3xl font-semibold tracking-tight text-[var(--ink)] sm:text-4xl">
          Git Activity Dashboard
        </h1>
        <p className="mt-2 max-w-2xl text-[var(--muted)]">
          Track repositories, sync GitHub activity into Postgres, and chart commits,
          PR turnaround, and contributors.
        </p>
      </header>

      <section className="mb-8 grid gap-3 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 sm:grid-cols-[1fr_auto_auto] sm:items-end">
        <label className="block text-sm">
          <span className="mb-1 block text-[var(--muted)]">
            Add repos (owner/repo, comma-separated)
          </span>
          <input
            className="w-full rounded border border-[var(--line)] bg-white px-3 py-2 outline-none focus:border-[var(--accent)]"
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            placeholder="owner/repo"
          />
        </label>
        <button
          type="button"
          onClick={handleTrack}
          disabled={busy}
          className="rounded bg-[var(--accent)] px-4 py-2 font-medium text-white disabled:opacity-60"
        >
          Track
        </button>
        <button
          type="button"
          onClick={handleSync}
          disabled={busy || repos.length === 0}
          className="rounded border border-[var(--accent)] bg-[var(--accent-soft)] px-4 py-2 font-medium text-[var(--accent)] disabled:opacity-60"
        >
          Sync now
        </button>
      </section>

      <section className="mb-6 flex flex-wrap items-end gap-4">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Repository</span>
          <select
            className="min-w-56 rounded border border-[var(--line)] bg-white px-3 py-2"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
          >
            <option value="">All tracked repos</option>
            {repos.map((repo) => (
              <option key={repo.id} value={repo.full_name}>
                {repo.full_name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Commit period</span>
          <select
            className="rounded border border-[var(--line)] bg-white px-3 py-2"
            value={period}
            onChange={(e) => setPeriod(e.target.value as 'day' | 'week')}
          >
            <option value="day">Per day</option>
            <option value="week">Per week</option>
          </select>
        </label>
        {status ? <p className="text-sm text-[var(--accent)]">{status}</p> : null}
        {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
          <h2 className="mt-0 mb-4 text-lg font-semibold">Commits over time</h2>
          <div className="h-72">
            {commits.length === 0 ? (
              <EmptyState text="No commit data yet. Track a repo and sync." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={commits}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#d7dee5" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#0f6e56"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
          <h2 className="mt-0 mb-4 text-lg font-semibold">Contributor leaderboard</h2>
          <div className="h-72">
            {contributors.length === 0 ? (
              <EmptyState text="No contributors yet." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={contributors.slice(0, 12)}
                  layout="vertical"
                  margin={{ left: 24 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#d7dee5" />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="author" width={90} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="commits" fill="#0f6e56" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 lg:col-span-2">
          <h2 className="mt-0 mb-4 text-lg font-semibold">PR turnaround (opened → merged)</h2>
          {turnaround.length === 0 ? (
            <EmptyState text="No merged PRs stored yet." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[var(--muted)]">
                    <th className="py-2 pr-3 font-medium">#</th>
                    <th className="py-2 pr-3 font-medium">Title</th>
                    <th className="py-2 pr-3 font-medium">Author</th>
                    <th className="py-2 pr-3 font-medium">Hours</th>
                    <th className="py-2 font-medium">Days</th>
                  </tr>
                </thead>
                <tbody>
                  {turnaround.map((pr) => (
                    <tr key={pr.number} className="border-b border-[var(--line)]">
                      <td className="py-2 pr-3 font-[var(--mono)]">{pr.number}</td>
                      <td className="py-2 pr-3">{pr.title}</td>
                      <td className="py-2 pr-3">{pr.author ?? '—'}</td>
                      <td className="py-2 pr-3">{pr.hours}</td>
                      <td className="py-2">{pr.days}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-[var(--muted)]">
      {text}
    </div>
  )
}

export default App
