# TAKAFLOW

Architecture and scope decisions live in [docs/architecture-blueprint.html](docs/architecture-blueprint.html) — read §22 (MVP) and §25 (resolved contradictions) before touching anything here.

Phase 1 (foundation scaffold) and Phase 2 (full database schema) are done. No API features yet — that starts at Phase 3.

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

## Schema (Phase 2, done)

All 12 tables from blueprint §08 exist as one Alembic migration (`backend/alembic/versions/723deff43d87_initial_schema.py`), applied to the local `takaflow` database: `user`, `collection_point`, `material`, `collection_point_material`, `material_rate`, `collection_transaction`, `payment`, `inventory_ledger`, `inventory_summary`, `device`, `sync_log`, `audit_log`. No `supplier`, `buyer`, `buyer_request`, `material_transfer`, or `prediction` tables — those are future scope per §22/§25.

One deliberate deviation from §08's wording: every `material_rate` row is tied to a specific branch (`collection_point_id` is `NOT NULL`, not an optional "global default"). Postgres unique indexes treat two `NULL`s as distinct, so a nullable branch column would have silently let two "global" rates for the same material both count as current — the exact kind of bug this project's ledger design exists to prevent. Simpler and correct beats matching the diagram literally.

`backend/tests/test_inventory_constraints.py` proves the negative-inventory `CHECK` constraints actually reject bad data against the real database, not a mock.

## Next: Phase 3

Auth & RBAC — login, JWT/refresh tokens, and role guards enforcing the §06 permissions matrix. See §21 for the full phase sequence and §22 for what's actually in scope this build.
