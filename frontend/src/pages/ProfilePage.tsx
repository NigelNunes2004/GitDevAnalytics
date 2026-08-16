import { useState, type FormEvent } from 'react'
import { api, type User } from '../api'

type Props = {
  user: User
  onUserUpdated: (user: User) => void
}

export function ProfilePage({ user, onUserUpdated }: Props) {
  const [displayName, setDisplayName] = useState(user.display_name ?? '')
  const [githubUsername, setGithubUsername] = useState(user.github_username ?? '')
  const [avatarUrl, setAvatarUrl] = useState(user.avatar_url ?? '')
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setStatus('')
    try {
      const updated = await api.saveProfile({
        display_name: displayName,
        github_username: githubUsername,
        avatar_url: avatarUrl,
      })
      onUserUpdated(updated)
      setStatus('Profile saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  function handlePhoto(file: File | null) {
    if (!file) return
    if (file.size > 280_000) {
      setError('Image too large. Keep under ~280KB, or paste an image URL instead.')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result ?? '')
      setAvatarUrl(result)
      setError('')
    }
    reader.readAsDataURL(file)
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Profile</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Photo, display name, and GitHub username for your account.
        </p>
      </header>

      <section className="gh-panel max-w-xl p-5">
        <form onSubmit={handleSave} className="space-y-4">
          <div className="flex items-center gap-4">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt=""
                className="h-16 w-16 rounded-full border border-[var(--line)] object-cover"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--surface-2)] text-lg font-semibold">
                {(displayName || user.email).slice(0, 1).toUpperCase()}
              </div>
            )}
            <label className="text-sm">
              <span className="mb-1 block font-medium">Upload photo</span>
              <input
                type="file"
                accept="image/*"
                className="block w-full text-xs text-[var(--muted)]"
                onChange={(e) => handlePhoto(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-1 block font-medium">Display name</span>
            <input
              className="gh-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium">GitHub username</span>
            <input
              className="gh-input"
              value={githubUsername}
              onChange={(e) => setGithubUsername(e.target.value)}
              placeholder="octocat"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium">Photo URL (optional)</span>
            <input
              className="gh-input"
              value={avatarUrl.startsWith('data:') ? '' : avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://…"
            />
            {avatarUrl.startsWith('data:') ? (
              <span className="mt-1 block text-xs text-[var(--muted)]">
                Using uploaded image data (leave URL blank to keep it).
              </span>
            ) : null}
          </label>

          <p className="m-0 text-xs text-[var(--muted)]">Signed in as {user.email}</p>

          <button type="submit" disabled={busy} className="gh-btn gh-btn-primary">
            Save profile
          </button>
        </form>
        {status ? <p className="mt-3 text-sm text-[var(--accent-hover)]">{status}</p> : null}
        {error ? <p className="mt-3 text-sm text-[var(--warn)]">{error}</p> : null}
      </section>
    </div>
  )
}
