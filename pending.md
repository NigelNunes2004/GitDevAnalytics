# Pending — finish local work → deploy ($0)

Auth (1A+2B) and the core dashboard features are implemented. What’s left is mostly ops, secrets, and going live.

## You (local / portfolio polish)

- [ ] Confirm frontend + backend start clean after reboot (`docker compose up -d db`, uvicorn, `npm run dev`)
- [ ] Smoke-test: register → Settings (GitHub username + PAT) → track → sync → charts
- [ ] Change bootstrap admin password if you still use `admin@localhost` / `changeme`
- [ ] Generate a real `TOKEN_ENCRYPTION_KEY` for anything beyond throwaway local data  
  (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- [ ] Replace weak `JWT_SECRET=dev-only-change-me-in-production` before any public deploy
- [ ] Optional: rotate GitHub PAT if it was ever pasted into chat, screenshots, or a shared `.env`
- [ ] Commit/push any remaining local-only edits from your VS Code account (Cursor does not push)
- [ ] Optional README pass: screenshots, demo credentials note, “what I learned” polish for recruiters

## Small code/config gaps before deploy

- [ ] Update `render.yaml` env list to include `JWT_SECRET`, `TOKEN_ENCRYPTION_KEY`, `JWT_EXPIRE_MINUTES` (Blueprint still only lists older vars)
- [ ] Confirm CI has whatever env defaults auth needs (or relies on app defaults — fine for pytest)
- [ ] Optional: document webhook setup as “advanced / needs server `GITHUB_TOKEN`”

## Deploy — Supabase (database)

- [ ] Create free Supabase project
- [ ] Copy pooler/`DATABASE_URL` in SQLAlchemy form: `postgresql+psycopg2://...`
- [ ] Run `alembic upgrade head` against Supabase (or rely on backend container boot: migrations then uvicorn)
- [ ] Do **not** point local `.env` at prod unless you intend to

## Deploy — Render (backend)

- [ ] New Web Service from this repo, Docker, context/`Dockerfile` under `backend/`
- [ ] Free plan; health check `/health`
- [ ] Set secrets:
  - `DATABASE_URL` (Supabase)
  - `JWT_SECRET` (strong, unique)
  - `TOKEN_ENCRYPTION_KEY` (Fernet key)
  - `CORS_ORIGINS` (your Vercel URL, e.g. `https://….vercel.app`)
  - `SYNC_INTERVAL_MINUTES` (e.g. `60`)
  - Optional: `GITHUB_TOKEN` (webhooks / fallback only)
- [ ] Note free-tier cold start (~30–50s after ~15 min idle) in any demo script
- [ ] Smoke: `GET https://<render>/health` → `{"status":"ok"}`

## Deploy — Vercel (frontend)

- [ ] Import repo; Root Directory = `frontend`
- [ ] Build: `npm run build`; Output: `dist`
- [ ] Env: `VITE_API_BASE_URL=https://<your-render-service>.onrender.com`
- [ ] Redeploy after env change (Vite bakes the URL at build time)
- [ ] Open the site → register → Settings → PAT → track/sync against **prod** API

## Post-deploy checklist

- [ ] Register a fresh prod user (don’t reuse local JWT)
- [ ] Save GitHub credentials in Settings; confirm Sync works
- [ ] Confirm CORS: browser calls Render without blocked-origin errors
- [ ] Confirm data isolation: second account doesn’t see first account’s repos
- [ ] Optional: GitHub webhook → Render `/webhooks/github` (needs `GITHUB_WEBHOOK_SECRET` + server token)
- [ ] Add live demo URL to README / portfolio

## Explicitly out of scope (not blockers)

- GitHub OAuth login
- Password reset email
- Refresh tokens / Redis sessions
- Sharing repos between users

## Suggested order

1. Local smoke + strong secrets in mind
2. Supabase + migrate
3. Render + env
4. Vercel + `VITE_API_BASE_URL`
5. End-to-end prod smoke + README demo link
