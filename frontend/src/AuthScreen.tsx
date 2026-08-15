import { useState } from 'react'
import { api, setToken, type User } from './api'

type Props = {
  onAuthenticated: (user: User) => void
}

export function AuthScreen({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
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
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <h1 className="m-0 text-3xl font-semibold tracking-tight">Git Activity Dashboard</h1>
      <p className="mt-2 text-[var(--muted)]">
        {mode === 'login' ? 'Sign in to your account' : 'Create an account'}
      </p>
      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-3 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4"
      >
        <label className="block text-sm">
          <span className="mb-1 block text-[var(--muted)]">Email</span>
          <input
            type="email"
            required
            className="w-full rounded border border-[var(--line)] px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-[var(--muted)]">Password (min 8 chars)</span>
          <input
            type="password"
            required
            minLength={8}
            className="w-full rounded border border-[var(--line)] px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error ? <p className="m-0 text-sm text-[var(--warn)]">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-[var(--accent)] px-4 py-2 font-medium text-white disabled:opacity-60"
        >
          {mode === 'login' ? 'Sign in' : 'Register'}
        </button>
      </form>
      <button
        type="button"
        className="mt-4 text-sm text-[var(--accent)]"
        onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
      >
        {mode === 'login' ? 'Need an account? Register' : 'Have an account? Sign in'}
      </button>
    </div>
  )
}
