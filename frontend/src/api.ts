const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'gitdash_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (response.status === 401) {
    setToken(null)
  }

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed (${response.status})`)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function qs(params: Record<string, string | undefined>) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value)
  })
  const out = search.toString()
  return out ? `?${out}` : ''
}

export type User = {
  id: number
  email: string
  display_name: string | null
  avatar_url: string | null
  github_username: string | null
  token_configured: boolean
}

export type AuthResponse = {
  access_token: string
  token_type: string
  user: User
}

export type GitHubSettings = {
  github_username: string | null
  token_configured: boolean
  token_hint: string | null
}

export type Repository = {
  id: number
  owner: string
  name: string
  full_name: string
  created_at: string
}

export type CommitPoint = { date: string; count: number }
export type Contributor = { author: string; commits: number }
export type PRTurnaround = {
  number: number
  title: string
  author: string | null
  hours: number
  days: number
  created_at: string
  merged_at: string
}

export type SyncResponse = {
  results: Array<{
    repo: string
    commits_upserted: number
    pull_requests_upserted: number
    issues_upserted: number
    workflow_runs_upserted?: number
    reviews_updated?: number
    rate_limit_remaining: number | null
  }>
}

export type HealthScore = {
  repo: string
  score: number
  commits_last_7_days: number
  open_prs: number
  stale_prs: number
  open_issues: number
  stale_issues: number
  recent_ci_failures: number
}

export type StaleAlerts = {
  stale_days: number
  items: Array<{
    kind: string
    repo: string
    number: number
    title: string
    author: string | null
    age_days: number
    created_at: string
  }>
}

export type CiRun = {
  repo: string
  name: string
  status: string
  conclusion: string | null
  html_url: string | null
  run_started_at: string | null
  duration_seconds: number | null
}

export type ReviewLatency = {
  number: number
  title: string
  author: string | null
  hours_to_first_review: number
  days_to_first_review: number
  created_at: string
  first_review_at: string
}

export type LanguageStat = { language: string; bytes: number; percent: number }

export type CompareResponse = {
  a: {
    repo: string
    commits: number
    contributors: number
    open_prs: number
    merged_prs: number
    avg_pr_turnaround_hours: number | null
    avg_review_latency_hours: number | null
  }
  b: {
    repo: string
    commits: number
    contributors: number
    open_prs: number
    merged_prs: number
    avg_pr_turnaround_hours: number | null
    avg_review_latency_hours: number | null
  }
}

export type UptimeSummary = {
  total_checks: number
  up_percent: number
  latest: {
    checked_at: string
    ok: boolean
    latency_ms: number | null
    detail: string | null
  } | null
  recent: Array<{
    checked_at: string
    ok: boolean
    latency_ms: number | null
    detail: string | null
  }>
}

export const api = {
  register: (email: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>('/auth/me'),
  getGitHubSettings: () => request<GitHubSettings>('/settings/github'),
  saveGitHubSettings: (github_token: string, github_username?: string) =>
    request<GitHubSettings>('/settings/github', {
      method: 'PUT',
      body: JSON.stringify({
        github_token,
        ...(github_username ? { github_username } : {}),
      }),
    }),
  saveProfile: (payload: {
    display_name?: string | null
    github_username?: string | null
    avatar_url?: string | null
  }) =>
    request<User>('/settings/profile', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  listRepos: () => request<Repository[]>('/repos'),
  trackRepos: (repos: string[]) =>
    request<Repository[]>('/repos', {
      method: 'POST',
      body: JSON.stringify({ repos }),
    }),
  deleteRepo: (repoId: number) =>
    request<{ status: string; full_name: string }>(`/repos/${repoId}`, {
      method: 'DELETE',
    }),
  syncAll: () => request<SyncResponse>('/sync', { method: 'POST' }),
  commits: (repo?: string, period: 'day' | 'week' = 'day') =>
    request<CommitPoint[]>(`/stats/commits${qs({ period, repo })}`),
  contributors: (repo?: string) =>
    request<Contributor[]>(`/stats/contributors${qs({ repo })}`),
  prTurnaround: (repo?: string) =>
    request<PRTurnaround[]>(`/stats/pr-turnaround${qs({ repo })}`),
  health: (repo?: string) => request<HealthScore[]>(`/stats/health${qs({ repo })}`),
  stale: (repo?: string) => request<StaleAlerts>(`/stats/stale${qs({ repo })}`),
  ci: (repo?: string) => request<CiRun[]>(`/stats/ci${qs({ repo })}`),
  reviewLatency: (repo?: string) =>
    request<ReviewLatency[]>(`/stats/review-latency${qs({ repo })}`),
  languages: (repo?: string) => request<LanguageStat[]>(`/stats/languages${qs({ repo })}`),
  compare: (repoA: string, repoB: string) =>
    request<CompareResponse>(`/stats/compare${qs({ repo_a: repoA, repo_b: repoB })}`),
  uptime: () => request<UptimeSummary>('/uptime'),
  downloadExport: async (format: 'json' | 'csv', repo?: string) => {
    const headers: Record<string, string> = {}
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
    const response = await fetch(`${API_BASE}/export${qs({ format, repo })}`, { headers })
    if (response.status === 401) setToken(null)
    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || `Export failed (${response.status})`)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gitdash-export.${format}`
    a.click()
    URL.revokeObjectURL(url)
  },
}
