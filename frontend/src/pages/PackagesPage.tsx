import { useEffect, useState } from 'react'
import { api, type PackageItem } from '../api'

type Props = {
  tokenConfigured: boolean
}

export function PackagesPage({ tokenConfigured }: Props) {
  const [packageType, setPackageType] = useState('npm')
  const [items, setItems] = useState<PackageItem[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function load(type: string) {
    if (!tokenConfigured) return
    setBusy(true)
    setError('')
    try {
      setItems(await api.packages(type))
    } catch (err) {
      setItems([])
      setError(err instanceof Error ? err.message : 'Failed to load packages')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!tokenConfigured) return
    let cancelled = false
    setBusy(true)
    setError('')
    api
      .packages(packageType)
      .then((rows) => {
        if (!cancelled) setItems(rows)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setItems([])
        setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setBusy(false)
      })
    return () => {
      cancelled = true
    }
  }, [tokenConfigured, packageType])

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Packages</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          GitHub Packages for your account (requires{' '}
          <code className="font-[var(--mono)]">read:packages</code>).
        </p>
      </header>
      <section className="gh-panel flex flex-wrap items-end gap-3 p-4">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Package type</span>
          <select
            className="gh-select"
            value={packageType}
            onChange={(e) => setPackageType(e.target.value)}
          >
            <option value="npm">npm</option>
            <option value="container">container</option>
            <option value="maven">maven</option>
            <option value="rubygems">rubygems</option>
            <option value="nuget">nuget</option>
          </select>
        </label>
        <button type="button" className="gh-btn" disabled={busy} onClick={() => load(packageType)}>
          Refresh
        </button>
      </section>
      {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}
      <section className="gh-panel p-4">
        {items.length === 0 ? (
          <p className="m-0 text-sm text-[var(--muted)]">No packages of this type.</p>
        ) : (
          <ul className="m-0 list-none space-y-2 p-0">
            {items.map((p) => (
              <li
                key={`${p.package_type}-${p.id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--line)] bg-[var(--bg)] px-3 py-2 text-sm"
              >
                <div>
                  <p className="m-0 font-medium">{p.name}</p>
                  <p className="m-0 text-xs text-[var(--muted)]">
                    {p.package_type} · {p.visibility}
                  </p>
                </div>
                {p.html_url ? (
                  <a href={p.html_url} target="_blank" rel="noreferrer" className="gh-link text-xs">
                    Open
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
