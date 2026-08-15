const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed (${response.status})`)
  }

  return response.json() as Promise<T>
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
    rate_limit_remaining: number | null
  }>
}

export const api = {
  listRepos: () => request<Repository[]>('/repos'),
  trackRepos: (repos: string[]) =>
    request<Repository[]>('/repos', {
      method: 'POST',
      body: JSON.stringify({ repos }),
    }),
  syncAll: () => request<SyncResponse>('/sync', { method: 'POST' }),
  commits: (repo?: string, period: 'day' | 'week' = 'day') => {
    const params = new URLSearchParams({ period })
    if (repo) params.set('repo', repo)
    return request<CommitPoint[]>(`/stats/commits?${params}`)
  },
  contributors: (repo?: string) => {
    const params = new URLSearchParams()
    if (repo) params.set('repo', repo)
    const qs = params.toString()
    return request<Contributor[]>(`/stats/contributors${qs ? `?${qs}` : ''}`)
  },
  prTurnaround: (repo?: string) => {
    const params = new URLSearchParams()
    if (repo) params.set('repo', repo)
    const qs = params.toString()
    return request<PRTurnaround[]>(`/stats/pr-turnaround${qs ? `?${qs}` : ''}`)
  },
}
