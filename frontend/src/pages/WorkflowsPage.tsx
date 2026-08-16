import { useEffect, useState } from 'react'
import { api, type Repository, type WorkflowTemplate } from '../api'

type Props = {
  repos: Repository[]
  tokenConfigured: boolean
  selectedRepo: string
  onSelectRepo: (repo: string) => void
}

export function WorkflowsPage({
  repos,
  tokenConfigured,
  selectedRepo,
  onSelectRepo,
}: Props) {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .workflowTemplates()
      .then(setTemplates)
      .catch((err: Error) => setError(err.message))
  }, [])

  async function apply(templateId: string) {
    if (!selectedRepo) return
    setBusy(true)
    setError('')
    setStatus('')
    try {
      const result = await api.applyWorkflowTemplate(selectedRepo, templateId)
      setStatus(
        result.pr_url
          ? `${result.message} PR #${result.pr_number}: ${result.pr_url}`
          : result.message,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open PR')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Workflows</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Open a PR that adds a starter GitHub Actions workflow. Needs{' '}
          <code className="font-[var(--mono)]">workflow</code> + repo contents write.
        </p>
      </header>
      <section className="gh-panel flex flex-wrap items-end gap-3 p-4">
        <label className="text-sm">
          <span className="mb-1 block text-[var(--muted)]">Target repository</span>
          <select
            className="gh-select min-w-56"
            value={selectedRepo}
            onChange={(e) => onSelectRepo(e.target.value)}
          >
            {repos.map((r) => (
              <option key={r.id} value={r.full_name}>
                {r.full_name}
              </option>
            ))}
          </select>
        </label>
      </section>
      {status ? <p className="text-sm text-[var(--accent-hover)]">{status}</p> : null}
      {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}
      <div className="grid gap-3">
        {templates.map((t) => (
          <section key={t.id} className="gh-panel p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="mt-0 mb-1 text-base font-semibold">{t.name}</h2>
                <p className="mt-0 mb-2 text-sm text-[var(--muted)]">{t.description}</p>
                <code className="font-[var(--mono)] text-xs text-[var(--ink)]">{t.path}</code>
              </div>
              <button
                type="button"
                className="gh-btn gh-btn-primary"
                disabled={busy || !selectedRepo || !tokenConfigured}
                onClick={() => apply(t.id)}
              >
                Open PR
              </button>
            </div>
            <pre className="mt-3 max-h-48 overflow-auto rounded-md border border-[var(--line)] bg-[var(--bg)] p-3 text-xs text-[var(--muted)]">
              {t.content}
            </pre>
          </section>
        ))}
      </div>
    </div>
  )
}
