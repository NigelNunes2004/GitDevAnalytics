import { useEffect, useState } from 'react'
import { api, type PackageItem } from '../api'

type Props = {
  open: boolean
  tokenConfigured: boolean
}

export function PackagesPanel({ open, tokenConfigured }: Props) {
  const [packageType, setPackageType] = useState('npm')
  const [items, setItems] = useState<PackageItem[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)

  async function load(type: string) {
    if (!tokenConfigured) return
    setBusy(true)
    setError('')
    try {
      setItems(await api.packages(type))
      setLoaded(true)
    } catch (err) {
      setItems([])
      setError(err instanceof Error ? err.message : 'Failed to load packages')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!open || !tokenConfigured || loaded) return
    let cancelled = false
    setBusy(true)
    setError('')
    api
      .packages(packageType)
      .then((rows) => {
        if (!cancelled) {
          setItems(rows)
          setLoaded(true)
        }
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
  }, [open, tokenConfigured, packageType, loaded])

  useEffect(() => {
    if (!open) {
      setLoaded(false)
      setItems([])
      setError('')
    }
  }, [open])

  if (!open) return null

  return (
    <div className="mt-3 rounded-md border border-[var(--line)] bg-[var(--bg)] p-3">
      <div className="mb-2 flex flex-wrap items-end gap-2">
        <label className="text-xs">
          <span className="mb-1 block text-[var(--muted)]">Type</span>
          <select
            className="gh-select text-xs"
            value={packageType}
            onChange={(e) => {
              setLoaded(false)
              setPackageType(e.target.value)
            }}
          >
            <option value="npm">npm</option>
            <option value="container">container</option>
            <option value="maven">maven</option>
            <option value="rubygems">rubygems</option>
            <option value="nuget">nuget</option>
          </select>
        </label>
        <button
          type="button"
          className="gh-btn text-xs"
          disabled={busy || !tokenConfigured}
          onClick={() => load(packageType)}
        >
          Refresh
        </button>
      </div>
      {!tokenConfigured ? (
        <p className="m-0 text-xs text-[#d29922]">Configure a PAT first.</p>
      ) : error ? (
        <p className="m-0 text-xs text-[var(--warn)]">{error}</p>
      ) : busy && items.length === 0 ? (
        <p className="m-0 text-xs text-[var(--muted)]">Loading…</p>
      ) : items.length === 0 ? (
        <p className="m-0 text-xs text-[var(--muted)]">No packages of this type.</p>
      ) : (
        <ul className="m-0 max-h-48 list-none space-y-1.5 overflow-y-auto p-0">
          {items.map((p) => (
            <li
              key={`${p.package_type}-${p.id}`}
              className="flex items-center justify-between gap-2 rounded border border-[var(--line)] px-2 py-1.5 text-xs"
            >
              <div className="min-w-0">
                <p className="m-0 truncate font-medium">{p.name}</p>
                <p className="m-0 text-[var(--muted)]">
                  {p.package_type} · {p.visibility}
                </p>
              </div>
              {p.html_url ? (
                <a href={p.html_url} target="_blank" rel="noreferrer" className="gh-link shrink-0">
                  Open
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <p className="mb-0 mt-2 text-[10px] text-[var(--muted)]">
        GitHub Packages for your account · needs{' '}
        <code className="font-[var(--mono)]">read:packages</code>
      </p>
    </div>
  )
}
