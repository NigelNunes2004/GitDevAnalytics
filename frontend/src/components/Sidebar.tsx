import type { AppPage } from '../nav'

type Props = {
  page: AppPage
  onNavigate: (page: AppPage) => void
  userLabel: string
  avatarUrl: string | null
  onLogout: () => void
}

type IconKind =
  | 'grid'
  | 'repo'
  | 'compare'
  | 'shield'
  | 'status'
  | 'rocket'
  | 'bell'
  | 'flow'
  | 'gear'
  | 'user'

const ITEMS: { id: AppPage; label: string; icon: IconKind }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'repos', label: 'Repositories', icon: 'repo' },
  { id: 'compare', label: 'Compare', icon: 'compare' },
  { id: 'vulnerability', label: 'Vulnerability check', icon: 'shield' },
  { id: 'status', label: 'Commit status', icon: 'status' },
  { id: 'deployments', label: 'Deployments', icon: 'rocket' },
  { id: 'notifications', label: 'Notifications', icon: 'bell' },
  { id: 'workflows', label: 'Workflows', icon: 'flow' },
  { id: 'config', label: 'Configuration', icon: 'gear' },
  { id: 'profile', label: 'Profile', icon: 'user' },
]

function NavIcon({ kind }: { kind: IconKind }) {
  const common = 'fill-current'
  if (kind === 'grid') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M1.5 1.5h5v5h-5v-5zm8 0h5v5h-5v-5zm-8 8h5v5h-5v-5zm8 0h5v5h-5v-5z" />
      </svg>
    )
  }
  if (kind === 'repo') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5zm10.5-1.5h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8.75z" />
      </svg>
    )
  }
  if (kind === 'compare') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M5.06 3.5a.75.75 0 00-1.12-1L1.5 5.44a.75.75 0 000 1.12l2.44 2.94a.75.75 0 001.12-1L3.56 6.5h8.88l-1.5 1.94a.75.75 0 001.12 1l2.44-2.94a.75.75 0 000-1.12L12.06 2.5a.75.75 0 10-1.12 1L12.44 5.5H3.56z" />
      </svg>
    )
  }
  if (kind === 'shield') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M8 1l6 2v5c0 3.5-2.5 5.8-6 7-3.5-1.2-6-3.5-6-7V3l6-2z" />
      </svg>
    )
  }
  if (kind === 'status') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M8 0a8 8 0 100 16A8 8 0 008 0zm3.5 5.5L7 10 4.5 7.5l1-1L7 8l3.5-3.5 1 1z" />
      </svg>
    )
  }
  if (kind === 'rocket') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M14.5 1.5c-3 0-6 2-8 4L3 9l-2 5 5-2 3.5-3.5c2-2 4-5 4-8zM6 10l-1 3 3-1 2.5-2.5L6 10z" />
      </svg>
    )
  }
  if (kind === 'bell') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M8 1a4 4 0 014 4v2.5l1.5 2H2.5L4 7.5V5a4 4 0 014-4zm0 14a2 2 0 002-2H6a2 2 0 002 2z" />
      </svg>
    )
  }
  if (kind === 'flow') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M3 2h4v3H3V2zm6 0h4v3H9V2zM3 7h4v3H3V7zm6 4h4v3H9v-3zM5 5v2h2V5H5zm4 5v2h2v-2H9z" />
      </svg>
    )
  }
  if (kind === 'gear') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
        <path d="M8 4.75a3.25 3.25 0 100 6.5 3.25 3.25 0 000-6.5zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z" />
      </svg>
    )
  }
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className={common}>
      <path d="M8 8a3 3 0 100-6 3 3 0 000 6zm-5.5 6.5A5.5 5.5 0 018 9a5.5 5.5 0 015.5 5.5.75.75 0 01-.75.75h-9.5a.75.75 0 01-.75-.75z" />
    </svg>
  )
}

export function Sidebar({ page, onNavigate, userLabel, avatarUrl, onLogout }: Props) {
  return (
    <aside className="gh-sidebar sticky top-0 flex h-screen w-[240px] shrink-0 flex-col border-r border-[var(--line)] bg-[rgba(13,17,23,0.94)] backdrop-blur-md">
      <div className="flex items-center gap-2 border-b border-[var(--line)] px-4 py-4">
        <svg width="28" height="28" viewBox="0 0 16 16" aria-hidden className="fill-[var(--ink)]">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
        </svg>
        <div className="min-w-0">
          <p className="m-0 truncate text-sm font-semibold">GitDash</p>
          <p className="m-0 truncate text-[11px] text-[var(--muted)]">Activity Console</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2" aria-label="Main">
        {ITEMS.map((item) => {
          const active = page === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`gh-nav-item ${active ? 'gh-nav-item-active' : ''}`}
            >
              <NavIcon kind={item.icon} />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      <div className="border-t border-[var(--line)] p-3">
        <div className="mb-2 flex items-center gap-2">
          {avatarUrl ? (
            <img src={avatarUrl} alt="" className="h-8 w-8 rounded-full object-cover" />
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--surface-2)] text-xs font-semibold">
              {userLabel.slice(0, 1).toUpperCase()}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="m-0 truncate text-xs font-medium">{userLabel}</p>
          </div>
        </div>
        <button type="button" onClick={onLogout} className="gh-btn w-full text-xs">
          Sign out
        </button>
      </div>
    </aside>
  )
}
