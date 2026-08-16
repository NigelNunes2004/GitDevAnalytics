import { useState } from 'react'
import type { Repository } from '../api'

type Props = {
  repos: Repository[]
  selectedRepo: string
  busy: boolean
  status: string
  error: string
  onSelectRepo: (repo: string) => void
  onTrack: (names: string[]) => Promise<void>
  onDelete: () => Promise<void>
  onExport: (format: 'json' | 'csv') => Promise<void>
  onSync: () => Promise<void>
}

export function ReposPage({
  repos,
  selectedRepo,
  busy,
  status,
  error,
  onSelectRepo,
  onTrack,
  onDelete,
  onExport,
  onSync,
}: Props) {
  const [repoInput, setRepoInput] = useState('')

  async function handleTrack() {
    const names = repoInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    await onTrack(names)
    setRepoInput('')
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Repositories</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Track, sync, delete, and export repository activity.
        </p>
      </header>

      <section className="gh-panel grid gap-3 p-4 sm:grid-cols-[1fr_auto_auto]">
        <label className="block text-sm sm:col-span-1">
          <span className="mb-1 block text-[var(--muted)]">Add repos (owner/repo, comma-separated)</span>
          <input
            className="gh-input"
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            placeholder="owner/repo"
          />
        </label>
        <button
          type="button"
          onClick={handleTrack}
          disabled={busy || !repoInput.trim()}
          className="gh-btn gh-btn-primary self-end"
        >
          Track
        </button>
        <button
          type="button"
          onClick={onSync}
          disabled={busy || repos.length === 0}
          className="gh-btn self-end"
        >
          Sync all
        </button>
      </section>

      <section className="gh-panel p-4">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="text-sm">
            <span className="mb-1 block text-[var(--muted)]">Selected repo</span>
            <select
              className="gh-select min-w-56"
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
          <button
            type="button"
            onClick={onDelete}
            disabled={busy || !selectedRepo}
            className="gh-btn gh-btn-danger"
          >
            Delete selected
          </button>
          <button
            type="button"
            onClick={() => onExport('json')}
            disabled={busy}
            className="gh-btn"
          >
            Export JSON
          </button>
          <button type="button" onClick={() => onExport('csv')} disabled={busy} className="gh-btn">
            Export CSV
          </button>
        </div>

        {status ? <p className="text-sm text-[var(--accent-hover)]">{status}</p> : null}
        {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}

        {repos.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No repositories tracked yet.</p>
        ) : (
          <ul className="m-0 list-none space-y-2 p-0">
            {repos.map((repo) => (
              <li
                key={repo.id}
                className={`flex items-center justify-between rounded-md border border-[var(--line)] px-3 py-2 text-sm ${
                  selectedRepo === repo.full_name ? 'bg-[var(--accent-soft)]' : 'bg-[var(--bg)]'
                }`}
              >
                <button
                  type="button"
                  className="border-0 bg-transparent p-0 text-left font-medium text-[var(--ink)]"
                  onClick={() => onSelectRepo(repo.full_name)}
                >
                  {repo.full_name}
                </button>
                <span className="font-[var(--mono)] text-xs text-[var(--muted)]">#{repo.id}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
