import { useCallback, useEffect, useState } from 'react'
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
import { CursorBackdrop } from './CursorBackdrop'
import { PageTransition } from './components/PageTransition'
import { Sidebar } from './components/Sidebar'
import type { AppPage } from './nav'
import { ComparePage } from './pages/ComparePage'
import { ConfigPage } from './pages/ConfigPage'
import { DashboardPage } from './pages/DashboardPage'
import { ProfilePage } from './pages/ProfilePage'
import { ReposPage } from './pages/ReposPage'

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [page, setPage] = useState<AppPage>('dashboard')
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState('')
  const [compareRepoA, setCompareRepoA] = useState('')
  const [compareRepoB, setCompareRepoB] = useState('')
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
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
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
    setCompareRepoA((current) => current || (list[0]?.full_name ?? ''))
    setCompareRepoB(
      (current) =>
        current ||
        list.find((r) => r.full_name !== (list[0]?.full_name ?? ''))?.full_name ||
        list[1]?.full_name ||
        '',
    )
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
    if (!user || page !== 'compare' || !compareRepoA || !compareRepoB || compareRepoA === compareRepoB) {
      if (page !== 'compare') setCompare(null)
      return
    }
    api
      .compare(compareRepoA, compareRepoB)
      .then(setCompare)
      .catch((err: Error) => setError(err.message))
  }, [user, page, compareRepoA, compareRepoB])

  function handleLogout() {
    setToken(null)
    setUser(null)
    setRepos([])
    setPage('dashboard')
  }

  async function handleTrack(names: string[]) {
    setBusy(true)
    setError('')
    setStatus('')
    try {
      await api.trackRepos(names)
      await refreshRepos()
      if (names[0]) setSelectedRepo(names[0])
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
      await refreshRepos()
      await refreshStats('', period)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete repo')
    } finally {
      setBusy(false)
    }
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
      <>
        <CursorBackdrop />
        <div className="relative z-10 mx-auto flex min-h-screen items-center justify-center px-4">
          <p className="text-[var(--muted)]">Loading…</p>
        </div>
      </>
    )
  }

  if (!user) {
    return <AuthScreen onAuthenticated={setUser} />
  }

  const userLabel = user.display_name || user.github_username || user.email

  let pageContent = null
  if (page === 'dashboard') {
    pageContent = (
      <DashboardPage
        repos={repos}
        selectedRepo={selectedRepo}
        period={period}
        busy={busy}
        status={status}
        error={error}
        health={health}
        uptime={uptime}
        commits={commits}
        contributors={contributors}
        languages={languages}
        ciRuns={ciRuns}
        stale={stale}
        reviews={reviews}
        turnaround={turnaround}
        tokenConfigured={user.token_configured}
        onSelectRepo={setSelectedRepo}
        onPeriod={setPeriod}
        onSync={handleSync}
      />
    )
  } else if (page === 'repos') {
    pageContent = (
      <ReposPage
        repos={repos}
        selectedRepo={selectedRepo}
        busy={busy}
        status={status}
        error={error}
        onSelectRepo={setSelectedRepo}
        onTrack={handleTrack}
        onDelete={handleDelete}
        onExport={handleExport}
        onSync={handleSync}
      />
    )
  } else if (page === 'compare') {
    pageContent = (
      <ComparePage
        repos={repos}
        compareRepoA={compareRepoA}
        compareRepoB={compareRepoB}
        compare={compare}
        error={error}
        onChangeA={setCompareRepoA}
        onChangeB={setCompareRepoB}
      />
    )
  } else if (page === 'config') {
    pageContent = <ConfigPage user={user} onUserUpdated={setUser} />
  } else {
    pageContent = <ProfilePage user={user} onUserUpdated={setUser} />
  }

  return (
    <>
      <CursorBackdrop />
      <div className="relative z-10 flex min-h-screen">
        <Sidebar
          page={page}
          onNavigate={(next) => {
            setError('')
            setStatus('')
            setPage(next)
          }}
          userLabel={userLabel}
          avatarUrl={user.avatar_url}
          onLogout={handleLogout}
        />
        <div className="min-w-0 flex-1 overflow-x-hidden">
          <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
            <PageTransition page={page}>{pageContent}</PageTransition>
          </main>
        </div>
      </div>
    </>
  )
}

export default App
