# Pending — finish local work → deploy ($0)

Auth (1A+2B), dashboard, vuln check, and GitHub extras (status, deployments, notifications, packages, workflows, profile) are **implemented**. Remaining work is local verification, secrets, and going live.

---

## Priority order (start here)

Do these in order. Each phase should be fully checked off before moving on.

### P0 — Local smoke (you, ~30 min)

Prove the app works end-to-end on your machine before touching cloud services.

- [x] **1.** Start stack: `docker compose up -d db` → backend (`uvicorn`) → frontend (`npm run dev`)
- [x] **2.** Smoke path: register → **Configuration** (PAT) → **Profile** (GitHub username) → track a repo → **Sync** → confirm dashboard charts populate
- [x] **3.** Spot-check extras: Commit status (message + +/- lines), Vulnerability scan, at least one other nav page loads without errors
- [x] **4.** Change bootstrap admin password if you still use `admin@localhost` / `changeme`



### P1 — Secrets (you, ~15 min)

Required before any public deploy. Generate once; reuse the same values on Render.

- [x] **5.** Generate `TOKEN_ENCRYPTION_KEY`:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- [x] **6.** Replace weak `JWT_SECRET=dev-only-change-me-in-production` with a long random string (password manager or `openssl rand -hex 32`)
- [x] **7.** Optional: rotate GitHub PAT if it was ever pasted into chat, screenshots, or a shared `.env`



### P2 — Git hygiene (you, ~10 min)

- [x] **8.** Commit/push any local edits from VS Code (Cursor does not push for you)
- [x] **9.** Confirm GitHub Actions CI is green on `main` after push



### P3 — Supabase (database)

- [ ] **10.** Create free Supabase project
- [ ] **11.** Copy pooler `DATABASE_URL` in SQLAlchemy form: `postgresql+psycopg2://...`
- [ ] **12.** Run `alembic upgrade head` against Supabase (or rely on backend Docker boot: migrations then uvicorn)
- [ ] **13.** Do **not** point local `.env` at prod unless you intend to



### P4 — Render (backend)

- [ ] **14.** New Web Service from this repo — Docker, context/`Dockerfile` under `backend/`
- [ ] **15.** Free plan; health check `/health`
- [ ] **16.** Set env secrets:
  - `DATABASE_URL` (Supabase)
  - `JWT_SECRET` (strong, unique — same as P1)
  - `TOKEN_ENCRYPTION_KEY` (Fernet — same as P1)
  - `JWT_EXPIRE_MINUTES` (e.g. `10080`)
  - `CORS_ORIGINS` (your Vercel URL, e.g. `https://….vercel.app`)
  - `SYNC_INTERVAL_MINUTES` (e.g. `60`)
  - Optional: `GITHUB_TOKEN` (webhooks / scheduler fallback only)
- [ ] **17.** Smoke: `GET https://<render>/health` → `{"status":"ok"}`
- [ ] **18.** Note free-tier cold start (~30–50s after ~15 min idle) in demo script / README



### P5 — Vercel (frontend)

- [ ] **19.** Import repo; Root Directory = `frontend`
- [ ] **20.** Build: `npm run build`; Output: `dist`
- [ ] **21.** Env: `VITE_API_BASE_URL=https://<your-render-service>.onrender.com`
- [ ] **22.** Redeploy after env change (Vite bakes the URL at build time)
- [ ] **23.** Open site → register → Settings → PAT → track/sync against **prod** API



### P6 — Post-deploy validation

- [ ] **24.** Register a fresh prod user (don’t reuse local JWT)
- [ ] **25.** Save GitHub credentials; confirm Sync works
- [ ] **26.** Confirm CORS: browser → Render without blocked-origin errors
- [ ] **27.** Confirm data isolation: second account doesn’t see first account’s repos
- [ ] **28.** Add live demo URL to README / portfolio



### P7 — Optional polish (not blockers)

- [ ] README pass: screenshots, demo credentials note, “what I learned” for recruiters
- [ ] GitHub webhook → Render `/webhooks/github` (needs `GITHUB_WEBHOOK_SECRET` + server `GITHUB_TOKEN`)
- [ ] Widen PAT scopes for full extras (see below)

---



## PAT scopes (informational — not deploy blockers)

Core sync/charts need `repo` or `public_repo`. Extras are best-effort:


| Feature                              | Scope                                       |
| ------------------------------------ | ------------------------------------------- |
| Vuln: Dependabot / secret scanning   | `security_events` + enable features on repo |
| Commit status                        | `repo:status`                               |
| Deployments                          | `repo_deployment`                           |
| Notifications                        | `notifications`                             |
| Packages (Profile → GitHub Packages) | `read:packages` (empty if you publish none) |
| Workflow templates                   | `workflow`                                  |
| Profile import                       | `read:user`                                 |


INFO cards on Vulnerability check (“Dependabot unavailable”) mean GitHub returned nothing — fix repo settings and/or PAT, then re-save in Configuration.

---



## Done on the code side (agent)

- [x] Commit status: tip message + +/- lines + recent commits list
- [x] `render.yaml` includes `JWT_SECRET`, `TOKEN_ENCRYPTION_KEY`, `JWT_EXPIRE_MINUTES`
- [x] CI sets explicit `JWT_SECRET` for pytest (app defaults also work)

---



## Explicitly out of scope

- GitHub OAuth login
- Password reset email
- Refresh tokens / Redis sessions
- Sharing repos between users

