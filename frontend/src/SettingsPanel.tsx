import { useEffect, useState } from 'react'
import { api, type GitHubSettings } from './api'

type Props = {
  onClose: () => void
  onSaved: () => void
}

export function SettingsPanel({ onClose, onSaved }: Props) {
  const [username, setUsername] = useState('')
  const [token, setToken] = useState('')
  const [existing, setExisting] = useState<GitHubSettings | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .getGitHubSettings()
      .then((settings) => {
        setExisting(settings)
        setUsername(settings.github_username ?? '')
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setStatus('')
    try {
      const saved = await api.saveGitHubSettings(username.trim(), token.trim())
      setExisting(saved)
      setToken('')
      setStatus('GitHub credentials saved.')
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="mb-8 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="m-0 text-lg font-semibold">Settings — GitHub credentials</h2>
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-[var(--line)] px-3 py-1 text-sm"
        >
          Close
        </button>
      </div>
      <p className="mt-0 mb-4 text-sm text-[var(--muted)]">
        Sync uses <strong>your</strong> Personal Access Token (not a shared server token). Create a
        classic PAT with <code className="font-[var(--mono)]">public_repo</code> (or{' '}
        <code className="font-[var(--mono)]">repo</code> for private repos).
      </p>
      {existing?.token_configured ? (
        <p className="text-sm text-[var(--accent)]">
          Token configured{existing.token_hint ? ` (${existing.token_hint})` : ''}. Enter a new PAT
          below to replace it.
        </p>
      ) : (
        <p className="text-sm text-[var(--warn)]">No token saved yet — Sync will fail until you save one.</p>
      )}
      <form onSubmit={handleSave} className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block text-[var(--muted)]">GitHub username</span>
          <input
            required
            className="w-full rounded border border-[var(--line)] px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="bob"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-[var(--muted)]">GitHub PAT</span>
          <input
            required
            type="password"
            className="w-full rounded border border-[var(--line)] px-3 py-2"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="ghp_…"
            autoComplete="off"
          />
        </label>
        <div className="sm:col-span-2 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-[var(--accent)] px-4 py-2 font-medium text-white disabled:opacity-60"
          >
            Save
          </button>
          {status ? <span className="text-sm text-[var(--accent)]">{status}</span> : null}
          {error ? <span className="text-sm text-[var(--warn)]">{error}</span> : null}
        </div>
      </form>
    </section>
  )
}
