export type AppPage = 'dashboard' | 'repos' | 'compare' | 'config' | 'profile'

export const PAGE_LABELS: Record<AppPage, string> = {
  dashboard: 'Dashboard',
  repos: 'Repositories',
  compare: 'Compare',
  config: 'Configuration',
  profile: 'Profile',
}
