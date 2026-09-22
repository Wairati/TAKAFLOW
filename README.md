# TAKAFLOW

Architecture and scope decisions live in [docs/architecture-blueprint.html](docs/architecture-blueprint.html) — read §22 (MVP) and §25 (resolved contradictions) before touching anything here.

Phase 1 (foundation scaffold) is done: monorepo wiring, backend skeleton, CI. No features yet.

## Layout

```
apps/
  collection-app/   Offline-first PWA for branch staff (Vite + React + TS)
  admin-portal/     Thin admin SPA (Vite + React + TS)
packages/
  ui/               Shared components (empty until the first real screen)
  api-client/       Typed fetch client shared by both apps
  types/            Shared TS types mirroring backend schemas
backend/
  app/              FastAPI app: routers → services → models
  alembic/          Migrations (DB URL comes from backend/.env, not alembic.ini)
  tests/
```

`apps/public-site`, `apps/buyer-portal`, and `ml/` are deliberately not scaffolded — they're future scope per §22/§25 item 6, not part of the 2-week build.

## First-time setup

**Backend** — PostgreSQL 18 is already installed and running locally.

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

1. Create the database once, using your own postgres password (pgAdmin or `psql -U postgres`):
   ```sql
   CREATE DATABASE takaflow;
   ```
2. `copy .env.example .env` and fill in that password in `DATABASE_URL`.
3. Run migrations (none exist yet beyond the empty baseline): `.venv\Scripts\python -m alembic upgrade head`
4. Start the API: `.venv\Scripts\python -m uvicorn app.main:app --reload`
5. Confirm: `http://localhost:8000/api/v1/health` → `{"status":"ok"}`, and `/api/v1/health/db` once `.env` has the real password.

**Frontend** — from the repo root (already installed):

```
npm run dev:collection-app   # http://localhost:5173
npm run dev:admin-portal     # http://localhost:5174
```

Each app calls the backend's `/health` endpoint on load and shows the result — that round trip proves the monorepo wiring (app → `@takaflow/api-client` → FastAPI) works end to end.

## Tests

```
cd backend && .venv\Scripts\python -m pytest
```

## Next: Phase 2

Full schema from blueprint §08 (materials, collection points, collection transactions, the append-only inventory ledger) as Alembic migrations. See §21 for the full phase sequence and §22 for what's actually in scope this build.
