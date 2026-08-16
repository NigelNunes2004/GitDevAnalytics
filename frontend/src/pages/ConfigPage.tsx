import { useEffect, useState, type FormEvent } from 'react'
import { api, type GitHubSettings, type User } from '../api'

type Props = {
  user: User
  onUserUpdated: (user: User) => void
}

export function ConfigPage({ user, onUserUpdated }: Props) {
  const [token, setToken] = useState('')
  const [existing, setExisting] = useState<GitHubSettings | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .getGitHubSettings()
      .then(setExisting)
      .catch((err: Error) => setError(err.message))
  }, [])

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setStatus('')
    try {
      const saved = await api.saveGitHubSettings(
        token.trim(),
        user.github_username ?? undefined,
      )
      setExisting(saved)
      setToken('')
      setStatus('API token saved and verified with GitHub.')
      const me = await api.me()
      onUserUpdated(me)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Configuration</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Store your GitHub Personal Access Token for Sync. Username lives under Profile.
        </p>
      </header>

      <section className="gh-panel max-w-xl space-y-4 p-5">
        {existing?.token_configured ? (
          <p className="m-0 text-sm text-[var(--accent-hover)]">
            Token configured{existing.token_hint ? ` (${existing.token_hint})` : ''}. Enter a new PAT
            to replace it.
          </p>
        ) : (
          <p className="m-0 rounded-md border border-[rgba(248,81,73,0.4)] bg-[var(--warn-soft)] px-3 py-2 text-sm text-[var(--warn)]">
            No token saved yet — Sync will fail until you save one.
          </p>
        )}

        <p className="m-0 text-sm text-[var(--muted)]">
          Classic PAT scopes: <code className="font-[var(--mono)]">public_repo</code> or{' '}
          <code className="font-[var(--mono)]">repo</code> for private repos. Optional add-ons:{' '}
          <code className="font-[var(--mono)]">security_events</code> (vuln alerts),{' '}
          <code className="font-[var(--mono)]">repo:status</code>,{' '}
          <code className="font-[var(--mono)]">repo_deployment</code>,{' '}
          <code className="font-[var(--mono)]">notifications</code>,{' '}
          <code className="font-[var(--mono)]">read:user</code>,{' '}
          <code className="font-[var(--mono)]">read:packages</code>,{' '}
          <code className="font-[var(--mono)]">workflow</code> (open workflow PRs).
        </p>

        <form onSubmit={handleSave} className="space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">GitHub PAT</span>
            <input
              required
              type="password"
              className="gh-input"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_…"
              autoComplete="off"
            />
          </label>
          <button type="submit" disabled={busy} className="gh-btn gh-btn-primary">
            Save token
          </button>
        </form>
        {status ? <p className="m-0 text-sm text-[var(--accent-hover)]">{status}</p> : null}
        {error ? <p className="m-0 text-sm text-[var(--warn)]">{error}</p> : null}
      </section>
    </div>
  )
}
