"""Starter GitHub Actions workflow templates (opened as PRs)."""

from __future__ import annotations

TEMPLATES: list[dict[str, str]] = [
    {
        "id": "ci-python",
        "name": "Python CI (ruff + pytest)",
        "description": "Runs ruff and pytest on push/PR for a backend/ layout.",
        "path": ".github/workflows/gitdash-ci.yml",
        "content": """name: GitDash CI

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: ruff check app tests
      - run: pytest -q
        env:
          DATABASE_URL: sqlite+pysqlite:///:memory:
          GITHUB_TOKEN: test-token
          CORS_ORIGINS: http://localhost:5173
""",
    },
    {
        "id": "dependency-review",
        "name": "Dependency review",
        "description": (
            "Reviews dependency changes on pull requests "
            "(GitHub Dependency Review action)."
        ),
        "path": ".github/workflows/gitdash-dependency-review.yml",
        "content": """name: GitDash Dependency Review

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  dependency-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
""",
    },
    {
        "id": "security-codeql",
        "name": "CodeQL analyze",
        "description": "Basic CodeQL security analysis for a JavaScript/TypeScript frontend.",
        "path": ".github/workflows/gitdash-codeql.yml",
        "content": """name: GitDash CodeQL

on:
  push:
    branches: [main, master]
  pull_request:
  schedule:
    - cron: "0 6 * * 1"

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
      actions: read
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript-typescript
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
""",
    },
]
