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
import type {
  CiRun,
  CommitPoint,
  Contributor,
  HealthScore,
  LanguageStat,
  PRTurnaround,
  Repository,
  ReviewLatency,
  StaleAlerts,
  UptimeSummary,
} from '../api'

const PIE_COLORS = ['#2f81f7', '#3fb950', '#f78166', '#d29922', '#a371f7', '#39c5cf', '#f778ba']
const GRID = '#30363d'
const AXIS = '#8b949e'
const tooltipStyle = {
  backgroundColor: '#161b22',
  border: '1px solid #30363d',
  borderRadius: 6,
  color: '#e6edf3',
}

type Props = {
  repos: Repository[]
  selectedRepo: string
  period: 'day' | 'week'
  busy: boolean
  status: string
  error: string
  health: HealthScore[]
  uptime: UptimeSummary | null
  commits: CommitPoint[]
  contributors: Contributor[]
  languages: LanguageStat[]
  ciRuns: CiRun[]
  stale: StaleAlerts | null
  reviews: ReviewLatency[]
  turnaround: PRTurnaround[]
  tokenConfigured: boolean
  onSelectRepo: (repo: string) => void
  onPeriod: (period: 'day' | 'week') => void
  onSync: () => void
}

export function DashboardPage({
  repos,
  selectedRepo,
  period,
  busy,
  status,
  error,
  health,
  uptime,
  commits,
  contributors,
  languages,
  ciRuns,
  stale,
  reviews,
  turnaround,
  tokenConfigured,
  onSelectRepo,
  onPeriod,
  onSync,
}: Props) {
  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="m-0 text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
            Charts and health signals for your tracked repositories.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="mb-1 block text-[var(--muted)]">Repository</span>
            <select
              className="gh-select min-w-52"
              value={selectedRepo}
              onChange={(e) => onSelectRepo(e.target.value)}
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
              className="gh-select"
              value={period}
              onChange={(e) => onPeriod(e.target.value as 'day' | 'week')}
            >
              <option value="day">Per day</option>
              <option value="week">Per week</option>
            </select>
          </label>
          <button
            type="button"
            onClick={onSync}
            disabled={busy || repos.length === 0}
            className="gh-btn gh-btn-primary"
          >
            Sync now
          </button>
        </div>
      </header>

      {!tokenConfigured ? (
        <p className="rounded-md border border-[rgba(210,153,34,0.4)] bg-[rgba(210,153,34,0.12)] px-3 py-2 text-sm text-[#d29922]">
          GitHub PAT not configured — open Configuration before Sync.
        </p>
      ) : null}
      {status ? <p className="m-0 text-sm text-[var(--accent-hover)]">{status}</p> : null}
      {error ? <p className="m-0 max-w-3xl text-sm text-[var(--warn)]">{error}</p> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Repo health score">
          {health.length === 0 ? (
            <Empty text="Sync a repo to compute health." />
          ) : (
            <div className="space-y-3">
              {health.map((row) => (
                <div
                  key={row.repo}
                  className="rounded-md border border-[var(--line)] bg-[var(--bg)] p-3"
                >
                  <div className="mb-1 flex items-baseline justify-between gap-3">
                    <span className="font-medium">{row.repo}</span>
                    <span className="font-[var(--mono)] text-2xl text-[var(--accent-hover)]">
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
                    <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                    <XAxis dataKey="checked_at" hide />
                    <YAxis tick={{ fontSize: 12, fill: AXIS }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Line
                      type="monotone"
                      dataKey="latency_ms"
                      stroke="#58a6ff"
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
          <ChartOrEmpty empty={commits.length === 0} text="No commit data yet.">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={commits}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: AXIS }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: AXIS }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="count" stroke="#3fb950" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartOrEmpty>
        </Panel>

        <Panel title="Contributor leaderboard">
          <ChartOrEmpty empty={contributors.length === 0} text="No contributors yet.">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={contributors.slice(0, 12)} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: AXIS }} />
                <YAxis type="category" dataKey="author" width={90} tick={{ fontSize: 12, fill: AXIS }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="commits" fill="#2f81f7" />
              </BarChart>
            </ResponsiveContainer>
          </ChartOrEmpty>
        </Panel>

        <Panel title="Language / stack breakdown">
          <ChartOrEmpty empty={languages.length === 0} text="No language data yet.">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={languages.slice(0, 7)}
                  dataKey="percent"
                  nameKey="language"
                  outerRadius={90}
                  label={(props) => `${String(props.name ?? '')} ${Number(props.value ?? 0)}%`}
                >
                  {languages.slice(0, 7).map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
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
                          <a href={run.html_url} target="_blank" rel="noreferrer" className="gh-link">
                            {run.name}
                          </a>
                        ) : (
                          run.name
                        )}
                      </td>
                      <td className="py-2 pr-2 font-[var(--mono)]">{run.conclusion || run.status}</td>
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
                    <tr
                      key={`${item.kind}-${item.repo}-${item.number}`}
                      className="border-b border-[var(--line)]"
                    >
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

        <Panel title="Code review latency">
          {reviews.length === 0 ? (
            <Empty text="No review timestamps yet." />
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
    </div>
  )
}

function Panel({
  title,
  children,
  wide,
}: {
  title: string
  children: React.ReactNode
  wide?: boolean
}) {
  return (
    <section className={`gh-panel p-4 ${wide ? 'lg:col-span-2' : ''}`}>
      <h2 className="mt-0 mb-4 border-b border-[var(--line)] pb-2 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center text-sm text-[var(--muted)]">{text}</div>
  )
}

function ChartOrEmpty({
  empty,
  text,
  children,
}: {
  empty: boolean
  text: string
  children: React.ReactNode
}) {
  if (empty) return <Empty text={text} />
  return <div className="h-72">{children}</div>
}
