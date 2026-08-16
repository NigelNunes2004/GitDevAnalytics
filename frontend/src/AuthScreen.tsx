import { useState, type FormEvent } from 'react'
import { api, setToken, type User } from './api'
import { CursorBackdrop } from './CursorBackdrop'

type Props = {
  onAuthenticated: (user: User) => void
}

export function AuthScreen({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result =
        mode === 'login'
          ? await api.login(email.trim(), password)
          : await api.register(email.trim(), password)
      setToken(result.access_token)
      onAuthenticated(result.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Auth failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <CursorBackdrop />
      <div className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
        <div className="mb-6 flex items-center gap-3">
          <GitHubMark />
          <div>
            <h1 className="m-0 text-2xl font-semibold tracking-tight">Git Activity Dashboard</h1>
            <p className="m-0 mt-1 text-sm text-[var(--muted)]">
              {mode === 'login' ? 'Sign in to continue' : 'Create your account'}
            </p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="gh-panel space-y-3 p-5">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-[var(--ink)]">Email address</span>
            <input
              type="email"
              required
              className="gh-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-[var(--ink)]">Password</span>
            <input
              type="password"
              required
              minLength={8}
              className="gh-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>
          {error ? <p className="m-0 text-sm text-[var(--warn)]">{error}</p> : null}
          <button type="submit" disabled={busy} className="gh-btn gh-btn-primary w-full">
            {mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-[var(--muted)]">
          {mode === 'login' ? 'New here?' : 'Already have an account?'}{' '}
          <button
            type="button"
            className="gh-link border-0 bg-transparent p-0 text-sm"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      </div>
    </>
  )
}

function GitHubMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 16 16" aria-hidden className="shrink-0 fill-[var(--ink)]">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}
