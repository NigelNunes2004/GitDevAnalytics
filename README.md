# Git Activity Dashboard

Full-stack DevOps portfolio project: sync GitHub commits/PRs/issues into Postgres, aggregate engineering activity, and visualize it in a React dashboard.

> **Deploy note (Render free tier):** the backend container spins down after ~15 minutes idle. The first request after idle can take **30–50 seconds** (cold start). That is expected platform behavior, not an application bug.

## Architecture

```mermaid
flowchart LR
  subgraph local [Local Dev]
    FE[Vite React]
    BE[FastAPI]
    PG[(Postgres container)]
    FE -->|REST JSON| BE
    BE --> PG
    BE -->|PAT| GH[GitHub API]
  end
  subgraph deploy [Free-tier Deploy]
    Vercel[Vercel Frontend]
    Render[Render Backend]
    Supa[(Supabase Postgres)]
    Vercel --> Render
    Render --> Supa
    Render --> GH
  end
```

| Layer | Tech |
| --- | --- |
| Frontend | React + TypeScript (Vite), Tailwind CSS, Recharts |
| Backend | FastAPI, SQLAlchemy, Pydantic, APScheduler |
| Database | PostgreSQL (Docker locally, Supabase when deployed) |
| Migrations | Alembic (no `create_all()` in app startup) |
| Containers | Docker multi-stage images + docker-compose |
| CI | GitHub Actions: lint, pytest, frontend build, image builds |

## Features

1. Track `owner/repo` repositories
2. Sync commits, pull requests, and issues via the GitHub REST API (rate-limit aware)
3. Aggregation APIs: commits over time, PR turnaround, contributor leaderboard
4. Dashboard UI to chart the aggregates
5. Background refresh with APScheduler
6. Dockerized local stack + CI pipeline

## Quick start (local)

### Prerequisites

- Docker Desktop
- Python 3.12+ (3.14 works for local venv)
- Node 20+
- A GitHub Personal Access Token (classic: `public_repo` is enough for public repos)

### 1. Clone and configure env

```bash
cp .env.example .env
# Edit .env and set GITHUB_TOKEN=ghp_...
```

### 2. Start Postgres

```bash
docker compose up -d db
```

### 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)  
Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 5. Full stack via Docker (optional)

```bash
# Ensure GITHUB_TOKEN is set in .env
docker compose up --build
```

- Frontend: http://localhost:3000  
- Backend: http://localhost:8000  
- Postgres: localhost:5432

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/repos` | Track repos `{ "repos": ["owner/name"] }` |
| GET | `/repos` | List tracked repos |
| POST | `/sync` | Fetch GitHub data for all tracked repos |
| POST | `/repos/{id}/sync` | Sync one repo |
| GET | `/stats/commits?repo=&period=day\|week` | Commits over time |
| GET | `/stats/pr-turnaround?repo=` | Merged PR hours/days |
| GET | `/stats/contributors?repo=` | Commits per author |

## Environment variables / secrets

Secrets never belong in source control. The same variable **names** are used everywhere; only the **values** change per environment.

| Variable | Local | Render (backend) | Vercel (frontend) | GitHub Actions |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | `.env` → local Postgres or Supabase | Render dashboard secret | n/a | test override / unused |
| `GITHUB_TOKEN` | `.env` | Render dashboard secret | n/a | dummy for unit tests |
| `CORS_ORIGINS` | `.env` (includes Vite origin) | Must include your Vercel URL | n/a | test value |
| `SYNC_INTERVAL_MINUTES` | `.env` | Render env | n/a | n/a |
| `VITE_API_BASE_URL` | `frontend/.env` | n/a | Vercel env (Render API URL) | CI build arg |

**Why this matters:** swapping local Postgres for Supabase is a connection-string change only. The app code always reads `DATABASE_URL`.

### Supabase `DATABASE_URL` tip

Use the SQLAlchemy-friendly URL form:

```text
postgresql+psycopg2://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

(Exact host comes from the Supabase project connection panel.)

## Migrations (Alembic)

Schema changes are versioned SQL scripts under `backend/alembic/versions/`.

```bash
cd backend
alembic upgrade head          # apply
alembic revision -m "msg"     # create new revision after model changes
```

Run the same `alembic upgrade head` against Supabase before or as the Render service starts (the backend Docker image runs migrations on boot).

## Deployment ($0 free tier)

### 1. Database — Supabase

1. Create a free Supabase project
2. Copy the Postgres connection string into `DATABASE_URL`
3. From `backend/`, set `DATABASE_URL` and run `alembic upgrade head`

### 2. Backend — Render

1. New **Web Service** from this repo
2. Root directory / Dockerfile path: `backend`
3. Set env vars: `DATABASE_URL`, `GITHUB_TOKEN`, `CORS_ORIGINS` (your Vercel URL), `SYNC_INTERVAL_MINUTES`
4. Health check path: `/health`
5. Expect cold starts after idle spin-down on the free tier

### 3. Frontend — Vercel

1. Import the repo; set **Root Directory** to `frontend`
2. Build command: `npm run build`
3. Output directory: `dist`
4. Env: `VITE_API_BASE_URL=https://<your-render-service>.onrender.com`

## CI/CD

On every push/PR, [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs:

1. Backend ruff + pytest
2. Frontend lint + production build
3. Docker builds for backend and frontend images

## Project layout

```text
backend/           FastAPI app, Alembic, tests
frontend/          Vite React dashboard
docker-compose.yml Local frontend + backend + Postgres
.github/workflows  CI pipeline
.env.example       Documented env vars (copy to .env)
```

## What I learned

- **Env-driven config:** one codebase for local Postgres and Supabase by never hardcoding connection details
- **Alembic migrations:** schema as code that can be applied the same way in Docker and on managed Postgres
- **GitHub rate limits:** reading `X-RateLimit-*` headers and failing with a clear 503 instead of opaque crashes
- **Aggregation vs live API:** sync into Postgres, then chart from SQL/Python aggregates so the UI stays fast and within quota
- **APScheduler vs Celery:** in-process scheduling is enough for a single service; free-tier sleep means on-demand sync remains important
- **Multi-stage Docker + Compose:** smaller images, reproducible local stacks, networking by service name (`db`, `backend`)
- **CORS and split hosting:** Vite/Vercel origin must be explicitly allowed by FastAPI when the API lives on Render
- **CI as a gate:** lint, tests, and image builds on every push catch breakage before deploy

## License

MIT — use freely for portfolio and learning.
