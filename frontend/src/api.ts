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

export type VulnerabilityFinding = {
  id: number
  repo: string
  source: string
  rule_id: string
  severity: string
  title: string
  detail: string | null
  path: string | null
  html_url: string | null
  remediation: string | null
  scanned_at: string
}

export type VulnScanResponse = {
  results: Array<{
    repo: string
    findings_count: number
    rate_limit_remaining: number | null
  }>
  findings: VulnerabilityFinding[]
}

export type CommitStatusSummary = {
  repo: string
  ref: string
  state: string
  sha: string
  message: string | null
  author: string | null
  html_url: string | null
  additions: number
  deletions: number
  total_count: number
  statuses: Array<{
    context: string
    state: string
    description: string | null
    target_url: string | null
    created_at: string | null
  }>
  recent_commits: Array<{
    sha: string
    message: string
    author: string | null
    html_url: string | null
    additions: number
    deletions: number
    total: number
    committed_at: string | null
  }>
  rate_limit_remaining: number | null
}

export type DeploymentItem = {
  id: number
  environment: string
  ref: string
  sha: string
  task: string
  description: string | null
  created_at: string | null
  latest_state: string | null
  latest_description: string | null
  latest_url: string | null
}

export type NotificationItem = {
  id: string
  reason: string
  unread: boolean
  updated_at: string | null
  repo: string | null
  title: string
  type: string
  url: string | null
  latest_comment_url: string | null
}

export type PackageItem = {
  id: number
  name: string
  package_type: string
  visibility: string
  html_url: string | null
  created_at: string | null
  updated_at: string | null
}

export type WorkflowTemplate = {
  id: string
  name: string
  description: string
  path: string
  content: string
}

export type WorkflowApplyResult = {
  repo: string
  branch: string
  path: string
  pr_number: number | null
  pr_url: string | null
  message: string
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
  vulnFindings: (repo?: string) =>
    request<VulnerabilityFinding[]>(`/vuln/findings${qs({ repo })}`),
  vulnScan: (repo?: string) =>
    request<VulnScanResponse>(`/vuln/scan${qs({ repo })}`, { method: 'POST' }),
  commitStatus: (repo: string, ref?: string) =>
    request<CommitStatusSummary>(`/github/commit-status${qs({ repo, ref })}`),
  deployments: (repo: string) =>
    request<DeploymentItem[]>(`/github/deployments${qs({ repo })}`),
  notifications: (includeRead = false) =>
    request<NotificationItem[]>(
      `/github/notifications${qs({ include_read: includeRead ? 'true' : undefined })}`,
    ),
  packages: (package_type = 'npm') =>
    request<PackageItem[]>(`/github/packages${qs({ package_type })}`),
  enrichProfileFromGitHub: () =>
    request<User>('/settings/profile/from-github', { method: 'POST' }),
  workflowTemplates: () => request<WorkflowTemplate[]>('/github/workflow-templates'),
  applyWorkflowTemplate: (repo: string, template_id: string) =>
    request<WorkflowApplyResult>('/github/workflow-templates/apply', {
      method: 'POST',
      body: JSON.stringify({ repo, template_id }),
    }),
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
