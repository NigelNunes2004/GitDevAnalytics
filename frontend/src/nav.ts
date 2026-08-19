export type AppPage =
  | 'dashboard'
  | 'repos'
  | 'compare'
  | 'vulnerability'
  | 'status'
  | 'deployments'
  | 'notifications'
  | 'workflows'
  | 'config'
  | 'profile'

export const PAGE_LABELS: Record<AppPage, string> = {
  dashboard: 'Dashboard',
  repos: 'Repositories',
  compare: 'Compare',
  vulnerability: 'Vulnerability check',
  status: 'Commit status',
  deployments: 'Deployments',
  notifications: 'Notifications',
  workflows: 'Workflows',
  config: 'Configuration',
  profile: 'Profile',
}
