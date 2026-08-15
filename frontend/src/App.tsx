import { useCallback, useEffect, useState, type ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  api,
  getToken,
  setToken,
  type CiRun,
  type CommitPoint,
  type CompareResponse,
  type Contributor,
  type HealthScore,
  type LanguageStat,
  type PRTurnaround,
  type Repository,
  type ReviewLatency,
  type StaleAlerts,
  type UptimeSummary,
  type User,
} from './api'
import { AuthScreen } from './AuthScreen'
import { SettingsPanel } from './SettingsPanel'

const PIE_COLORS = ['#0f6e56', '#1d4e89', '#9a3412', '#854d0e', '#4c1d95', '#115e59', '#7c2d12']

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string>('')
  const [compareRepoA, setCompareRepoA] = useState<string>('')
  const [compareRepoB, setCompareRepoB] = useState<string>('')
  const [compareMode, setCompareMode] = useState(false)
  const [repoInput, setRepoInput] = useState('')
  const [period, setPeriod] = useState<'day' | 'week'>('day')
  const [commits, setCommits] = useState<CommitPoint[]>([])
  const [contributors, setContributors] = useState<Contributor[]>([])
  const [turnaround, setTurnaround] = useState<PRTurnaround[]>([])
  const [health, setHealth] = useState<HealthScore[]>([])
  const [stale, setStale] = useState<StaleAlerts | null>(null)
  const [ciRuns, setCiRuns] = useState<CiRun[]>([])
  const [reviews, setReviews] = useState<ReviewLatency[]>([])
  const [languages, setLanguages] = useState<LanguageStat[]>([])
  const [compare, setCompare] = useState<CompareResponse | null>(null)
  const [uptime, setUptime] = useState<UptimeSummary | null>(null)
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setAuthReady(true)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setAuthReady(true))
  }, [])

  const refreshRepos = useCallback(async () => {
    const list = await api.listRepos()
    setRepos(list)
    setSelectedRepo((current) => current || (list[0]?.full_name ?? ''))
  }, [])

  const refreshStats = useCallback(async (repo: string, commitPeriod: 'day' | 'week') => {
    const filter = repo || undefined
    const [
      commitData,
      contributorData,
      prData,
      healthData,
      staleData,
      ciData,
      reviewData,
      languageData,
      uptimeData,
    ] = await Promise.all([
      api.commits(filter, commitPeriod),
      api.contributors(filter),
      api.prTurnaround(filter),
      api.health(filter),
      api.stale(filter),
      api.ci(filter),
      api.reviewLatency(filter),
      api.languages(filter),
      api.uptime(),
    ])
    setCommits(commitData)
    setContributors(contributorData)
    setTurnaround(prData)
    setHealth(healthData)
    setStale(staleData)
    setCiRuns(ciData)
    setReviews(reviewData)
    setLanguages(languageData)
    setUptime(uptimeData)
  }, [])

  useEffect(() => {
    if (!user) return
    refreshRepos().catch((err: Error) => setError(err.message))
  }, [user, refreshRepos])

  useEffect(() => {
    if (!user) return
    refreshStats(selectedRepo, period).catch((err: Error) => setError(err.message))
  }, [user, selectedRepo, period, refreshStats, repos.length])

  useEffect(() => {
    if (!user || !compareMode || !compareRepoA || !compareRepoB || compareRepoA === compareRepoB) {
      setCompare(null)
      return
    }
    api
      .compare(compareRepoA, compareRepoB)
      .then(setCompare)
      .catch((err: Error) => setError(err.message))
  }, [user, compareMode, compareRepoA, compareRepoB])

  function handleHardReload() {
    window.location.reload()
  }

  function handleLogout() {
    setToken(null)
    setUser(null)
    setRepos([])
    setShowSettings(false)
  }

  async function handleExport(format: 'json' | 'csv') {
    setBusy(true)
    setError('')
    try {
      await api.downloadExport(format, selectedRepo || undefined)
      setStatus(`Exported ${format.toUpperCase()}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setBusy(false)
    }
  }

  if (!authReady) {
    return (
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4">
        <p className="text-[var(--muted)]">Loading…</p>
      </div>
    )
  }

  if (!user) {
    return <AuthScreen onAuthenticated={setUser} />
  }

  function enableCompareMode() {
    const first = selectedRepo || repos[0]?.full_name || ''
    const second =
      repos.find((repo) => repo.full_name !== first)?.full_name ?? repos[1]?.full_name ?? ''
    setCompareRepoA(first)
    setCompareRepoB(second)
    setCompareMode(true)
  }

  function disableCompareMode() {
    setCompareMode(false)
    setCompare(null)
    setCompareRepoA('')
    setCompareRepoB('')
  }

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
            `${r.repo}: ${r.commits_upserted} commits, ${r.pull_requests_upserted} PRs, ${r.workflow_runs_upserted ?? 0} CI runs`,
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

  async function handleDelete() {
    const target = repos.find((repo) => repo.full_name === selectedRepo)
    if (!target) return
    const ok = window.confirm(
      `Remove ${target.full_name} from tracking? Synced commits/PRs/issues for it will be deleted.`,
    )
    if (!ok) return

    setBusy(true)
    setError('')
    setStatus('')
    try {
      await api.deleteRepo(target.id)
      setStatus(`Deleted ${target.full_name}`)
      setSelectedRepo('')
      if (compareRepoA === target.full_name || compareRepoB === target.full_name) {
        disableCompareMode()
      }
      await refreshRepos()
      await refreshStats('', period)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete repo')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-8 border-b border-[var(--line)] pb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 font-[var(--mono)] text-xs tracking-[0.14em] text-[var(--muted)] uppercase">
              DevOps portfolio tool
            </p>
            <h1 className="m-0 text-3xl font-semibold tracking-tight text-[var(--ink)] sm:text-4xl">
              Git Activity Dashboard
            </h1>
            <p className="mt-2 max-w-2xl text-[var(--muted)]">
              Track repositories, sync GitHub activity into Postgres, and chart engineering health —
              commits, CI, reviews, languages, and uptime.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-[var(--muted)]">{user.email}</span>
            <button
              type="button"
              onClick={() => setShowSettings((v) => !v)}
              className="rounded border border-[var(--line)] px-3 py-1.5 font-medium"
            >
              Settings
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded border border-[var(--line)] px-3 py-1.5 font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {showSettings ? (
        <SettingsPanel
          onClose={() => setShowSettings(false)}
          onSaved={() => {
            api.me().then(setUser).catch(() => undefined)
          }}
        />
      ) : null}

      {!user.token_configured && !showSettings ? (
        <p className="mb-4 rounded border border-[var(--warn)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--warn)]">
          GitHub PAT not configured — open Settings before Sync.
        </p>
      ) : null}

      <section className="mb-8 grid gap-3 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 sm:grid-cols-[1fr_repeat(6,auto)] sm:items-end">
        <label className="block text-sm sm:col-span-1">
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
        <button
          type="button"
          onClick={compareMode ? disableCompareMode : enableCompareMode}
          disabled={!compareMode && repos.length < 2}
          className="rounded border border-[var(--line)] px-4 py-2 text-sm font-medium text-[var(--ink)] disabled:opacity-60"
          title={
            repos.length < 2 && !compareMode
              ? 'Track at least two repos to compare'
              : undefined
          }
        >
          {compareMode ? 'Close compare' : 'Compare'}
        </button>
        <button
          type="button"
          onClick={handleHardReload}
          className="rounded border border-[var(--line)] px-4 py-2 text-sm font-medium text-[var(--ink)]"
        >
          Reload
        </button>
        <button
          type="button"
          onClick={() => handleExport('json')}
          disabled={busy}
          className="rounded border border-[var(--line)] px-4 py-2 text-center text-sm font-medium text-[var(--ink)] disabled:opacity-60"
        >
          Export JSON
        </button>
        <button
          type="button"
          onClick={() => handleExport('csv')}
          disabled={busy}
          className="rounded border border-[var(--line)] px-4 py-2 text-center text-sm font-medium text-[var(--ink)] disabled:opacity-60"
        >
          Export CSV
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
        <button
          type="button"
          onClick={handleDelete}
          disabled={busy || !selectedRepo}
          className="rounded border border-[var(--warn)] px-4 py-2 text-sm font-medium text-[var(--warn)] disabled:opacity-60"
          title={!selectedRepo ? 'Select a specific repo to delete' : 'Delete selected repo'}
        >
          Delete
        </button>
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
        {error ? <p className="max-w-xl text-sm text-[var(--warn)]">{error}</p> : null}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Repo health score">
          {health.length === 0 ? (
            <Empty text="Sync a repo to compute health." />
          ) : (
            <div className="space-y-3">
              {health.map((row) => (
                <div key={row.repo} className="rounded border border-[var(--line)] p-3">
                  <div className="mb-1 flex items-baseline justify-between gap-3">
                    <span className="font-medium">{row.repo}</span>
                    <span className="font-[var(--mono)] text-2xl text-[var(--accent)]">
                      {row.score}
                    </span>
                  </div>
                  <p className="m-0 text-xs text-[var(--muted)]">
                    {row.commits_last_7_days} commits/7d · {row.stale_prs} stale PRs ·{' '}
                    {row.stale_issues} stale issues · {row.recent_ci_failures} CI fails
                  </p>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="API uptime">
          {!uptime ? (
            <Empty text="No uptime samples yet." />
          ) : (
            <>
              <p className="mt-0 mb-3 text-sm text-[var(--muted)]">
                {uptime.up_percent}% up across {uptime.total_checks} checks
                {uptime.latest
                  ? ` · latest ${uptime.latest.ok ? 'OK' : 'DOWN'} (${uptime.latest.latency_ms ?? '—'} ms)`
                  : ''}
              </p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={uptime.recent}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#d7dee5" />
                    <XAxis dataKey="checked_at" hide />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="latency_ms"
                      stroke="#1d4e89"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </Panel>

        <Panel title="Commits over time">
          <ChartOrEmpty empty={commits.length === 0} text="No commit data yet. Track a repo and sync.">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={commits}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d7dee5" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#0f6e56" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartOrEmpty>
        </Panel>

        <Panel title="Contributor leaderboard">
          <ChartOrEmpty empty={contributors.length === 0} text="No contributors yet.">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={contributors.slice(0, 12)} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d7dee5" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="author" width={90} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="commits" fill="#0f6e56" />
              </BarChart>
            </ResponsiveContainer>
          </ChartOrEmpty>
        </Panel>

        <Panel title="Language / stack breakdown">
          <ChartOrEmpty empty={languages.length === 0} text="No language data yet. Sync again.">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={languages.slice(0, 7)}
                  dataKey="percent"
                  nameKey="language"
                  outerRadius={90}
                  label={(props) => {
                    const name = String(props.name ?? '')
                    const value = Number(props.value ?? 0)
                    return `${name} ${value}%`
                  }}
                >
                  {languages.slice(0, 7).map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </ChartOrEmpty>
        </Panel>

        <Panel title="CI status snapshot">
          {ciRuns.length === 0 ? (
            <Empty text="No workflow runs stored yet." />
          ) : (
            <div className="max-h-72 overflow-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[var(--muted)]">
                    <th className="py-2 pr-2 font-medium">Workflow</th>
                    <th className="py-2 pr-2 font-medium">Result</th>
                    <th className="py-2 font-medium">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {ciRuns.map((run, idx) => (
                    <tr key={`${run.name}-${idx}`} className="border-b border-[var(--line)]">
                      <td className="py-2 pr-2">
                        {run.html_url ? (
                          <a href={run.html_url} target="_blank" rel="noreferrer" className="text-[var(--accent)]">
                            {run.name}
                          </a>
                        ) : (
                          run.name
                        )}
                      </td>
                      <td className="py-2 pr-2 font-[var(--mono)]">
                        {run.conclusion || run.status}
                      </td>
                      <td className="py-2">
                        {run.duration_seconds != null ? `${Math.round(run.duration_seconds)}s` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title={`Stale alerts (>${stale?.stale_days ?? 14}d)`} wide>
          {!stale || stale.items.length === 0 ? (
            <Empty text="No stale open PRs or issues." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[var(--muted)]">
                    <th className="py-2 pr-3 font-medium">Type</th>
                    <th className="py-2 pr-3 font-medium">Repo</th>
                    <th className="py-2 pr-3 font-medium">#</th>
                    <th className="py-2 pr-3 font-medium">Title</th>
                    <th className="py-2 font-medium">Age (days)</th>
                  </tr>
                </thead>
                <tbody>
                  {stale.items.map((item) => (
                    <tr key={`${item.kind}-${item.repo}-${item.number}`} className="border-b border-[var(--line)]">
                      <td className="py-2 pr-3 uppercase">{item.kind}</td>
                      <td className="py-2 pr-3">{item.repo}</td>
                      <td className="py-2 pr-3 font-[var(--mono)]">{item.number}</td>
                      <td className="py-2 pr-3">{item.title}</td>
                      <td className="py-2">{item.age_days}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="Code review latency (open → first review)">
          {reviews.length === 0 ? (
            <Empty text="No review timestamps yet. Sync again to fetch reviews." />
          ) : (
            <div className="max-h-72 overflow-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[var(--muted)]">
                    <th className="py-2 pr-2 font-medium">#</th>
                    <th className="py-2 pr-2 font-medium">Title</th>
                    <th className="py-2 font-medium">Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((row) => (
                    <tr key={row.number} className="border-b border-[var(--line)]">
                      <td className="py-2 pr-2 font-[var(--mono)]">{row.number}</td>
                      <td className="py-2 pr-2">{row.title}</td>
                      <td className="py-2">{row.hours_to_first_review}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        {compareMode ? (
          <Panel title="Compare mode" wide>
            <div className="space-y-4">
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-sm">
                  <span className="mb-1 block text-[var(--muted)]">Repo A</span>
                  <select
                    className="min-w-48 rounded border border-[var(--line)] bg-white px-3 py-2"
                    value={compareRepoA}
                    onChange={(e) => setCompareRepoA(e.target.value)}
                  >
                    {repos.map((repo) => (
                      <option key={`a-${repo.id}`} value={repo.full_name}>
                        {repo.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-[var(--muted)]">Repo B</span>
                  <select
                    className="min-w-48 rounded border border-[var(--line)] bg-white px-3 py-2"
                    value={compareRepoB}
                    onChange={(e) => setCompareRepoB(e.target.value)}
                  >
                    {repos.map((repo) => (
                      <option key={`b-${repo.id}`} value={repo.full_name}>
                        {repo.full_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {!compare || compareRepoA === compareRepoB ? (
                <Empty text="Pick two different repos to see the comparison." />
              ) : (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <CompareCard side={compare.a} />
                  <CompareCard side={compare.b} />
                </div>
              )}
            </div>
          </Panel>
        ) : null}

        <Panel title="PR turnaround (opened → merged)" wide>
          {turnaround.length === 0 ? (
            <Empty text="No merged PRs stored yet." />
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
        </Panel>
      </div>

      <p className="mt-8 text-xs text-[var(--muted)]">
        Webhook endpoint for live updates: <code className="font-[var(--mono)]">POST /webhooks/github</code>
        {' '}(optional <code className="font-[var(--mono)]">GITHUB_WEBHOOK_SECRET</code>). Auth/multi-user is intentionally deferred.
      </p>
    </div>
  )
}

function Panel({
  title,
  children,
  wide,
}: {
  title: string
  children: ReactNode
  wide?: boolean
}) {
  return (
    <section
      className={`rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 ${wide ? 'lg:col-span-2' : ''}`}
    >
      <h2 className="mt-0 mb-4 text-lg font-semibold">{title}</h2>
      {children}
    </section>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center text-sm text-[var(--muted)]">
      {text}
    </div>
  )
}

function ChartOrEmpty({
  empty,
  text,
  children,
}: {
  empty: boolean
  text: string
  children: ReactNode
}) {
  if (empty) return <Empty text={text} />
  return <div className="h-72">{children}</div>
}

function CompareCard({
  side,
}: {
  side: CompareResponse['a']
}) {
  return (
    <div className="rounded border border-[var(--line)] p-3">
      <p className="mt-0 mb-2 font-medium">{side.repo}</p>
      <ul className="m-0 list-none space-y-1 p-0 text-[var(--muted)]">
        <li>Commits: {side.commits}</li>
        <li>Contributors: {side.contributors}</li>
        <li>Open PRs: {side.open_prs}</li>
        <li>Merged PRs: {side.merged_prs}</li>
        <li>Avg turnaround: {side.avg_pr_turnaround_hours ?? '—'} h</li>
        <li>Avg first review: {side.avg_review_latency_hours ?? '—'} h</li>
      </ul>
    </div>
  )
}

export default App
