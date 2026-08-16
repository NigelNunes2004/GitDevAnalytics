import type { CompareResponse, Repository } from '../api'

type Props = {
  repos: Repository[]
  compareRepoA: string
  compareRepoB: string
  compare: CompareResponse | null
  error: string
  onChangeA: (repo: string) => void
  onChangeB: (repo: string) => void
}

export function ComparePage({
  repos,
  compareRepoA,
  compareRepoB,
  compare,
  error,
  onChangeA,
  onChangeB,
}: Props) {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="m-0 text-2xl font-semibold">Compare</h1>
        <p className="mt-1 mb-0 text-sm text-[var(--muted)]">
          Side-by-side activity metrics for two tracked repositories.
        </p>
      </header>

      {repos.length < 2 ? (
        <div className="gh-panel p-6 text-sm text-[var(--muted)]">
          Track at least two repositories to use Compare.
        </div>
      ) : (
        <section className="gh-panel space-y-4 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm">
              <span className="mb-1 block text-[var(--muted)]">Repo A</span>
              <select
                className="gh-select min-w-48"
                value={compareRepoA}
                onChange={(e) => onChangeA(e.target.value)}
              >
                {repos.map((repo) => (
                  <option key={`a-${repo.id}`} value={repo.full_name}>
                    {repo.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-[var(--muted)]">Repo B</span>
              <select
                className="gh-select min-w-48"
                value={compareRepoB}
                onChange={(e) => onChangeB(e.target.value)}
              >
                {repos.map((repo) => (
                  <option key={`b-${repo.id}`} value={repo.full_name}>
                    {repo.full_name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error ? <p className="text-sm text-[var(--warn)]">{error}</p> : null}

          {!compare || compareRepoA === compareRepoB ? (
            <p className="text-sm text-[var(--muted)]">Pick two different repos to see the comparison.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <CompareCard side={compare.a} />
              <CompareCard side={compare.b} />
            </div>
          )}
        </section>
      )}
    </div>
  )
}

function CompareCard({ side }: { side: CompareResponse['a'] }) {
  return (
    <div className="rounded-md border border-[var(--line)] bg-[var(--bg)] p-4">
      <p className="mt-0 mb-3 text-base font-semibold">{side.repo}</p>
      <ul className="m-0 list-none space-y-2 p-0 text-sm text-[var(--muted)]">
        <li>Commits: {side.commits}</li>
        <li>Contributors: {side.contributors}</li>
        <li>Open PRs: {side.open_prs}</li>
        <li>Merged PRs: {side.merged_prs}</li>
        <li>Avg turnaround: {side.avg_pr_turnaround_hours ?? '—'} h</li>
        <li>Avg first review: {side.avg_review_latency_hours ?? '—'} h</li>
      </ul>
    </div>
  )
}
