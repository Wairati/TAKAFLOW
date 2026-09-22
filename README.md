# TAKAFLOW

Architecture and scope decisions live in [docs/architecture-blueprint.html](docs/architecture-blueprint.html) — read §22 (MVP) and §25 (resolved contradictions) before touching anything here.

Phases 1–9 (the full core MVP per §22) plus Phase 12 (public site) are done. What remains is polish, not new architecture — see "Next" below.

## Layout

```
apps/
  collection-app/   Offline-first PWA for branch staff (Vite + React + TS)
  admin-portal/     Thin admin SPA (Vite + React + TS)
  public-site/      Read-only public site, no auth (Vite + React + TS)
packages/
  ui/               Shared auth/login + components used by collection-app and admin-portal
  api-client/       Typed fetch client shared by all three apps
  types/            Shared TS types mirroring backend schemas
backend/
  app/              FastAPI app: routers → services → models
  alembic/          Migrations (DB URL comes from backend/.env, not alembic.ini)
  tests/
```

`apps/buyer-portal` and `ml/` are deliberately not scaffolded — they're future scope per §22/§25 item 6, not part of this build.

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

## Auth & RBAC (Phase 3, done)

Two roles only for this build: `admin` and `collection_point_staff` (`buyer` deferred with the buyer portal, §22). Endpoints, all under `/api/v1/auth`:

- `POST /login` — email + password → access token (15 min JWT) + refresh token
- `POST /refresh` — rotates the refresh token: the one presented is revoked and a new pair issued; replaying an already-used refresh token fails
- `POST /logout` — revokes a refresh token
- `GET /me` — current user's identity, for the frontend to bootstrap on load
- `POST /users` — admin-only, creates staff/admin accounts (no self-registration, §06)

Refresh tokens are stored as a SHA-256 hash only (`refresh_token` table) — a database leak alone can't be replayed as a live session. `backend/app/core/deps.py` has the two reusable guards every future route will use: `require_role(...)` and `require_own_collection_point(...)`.

There's no admin account yet anywhere — the very first one has to be created directly against the database, since nothing can call the admin-only `/users` endpoint yet. Run this once:
```
cd backend
.venv\Scripts\python -m app.scripts.create_admin
```
It asks for an email, name, and password, and creates that user as an admin. Every account after that should go through `POST /auth/users` instead.

## Collection points & materials (Phase 4, done)

Admin CRUD over `/api/v1/collection-points` and `/api/v1/materials` — reads are open to any authenticated user, writes (`POST`/`PATCH`/`DELETE`) require the admin role via `require_role(...)` from Phase 3. No schema changes were needed — Phase 2 already had every table this phase's endpoints touch.

The core piece is per-point material acceptance and rate history (§08 challenges 2 & 3), nested under a collection point:

- `POST /collection-points/{id}/materials` — start accepting a material at a branch, at a given rate
- `PATCH /collection-points/{id}/materials/{material_id}/rate` — change the rate: closes the currently-open `material_rate` row (`effective_to = now`) and inserts a new one, rather than overwriting the rate in place — so the rate that was actually applied to a past transaction is never lost
- `DELETE /collection-points/{id}/materials/{material_id}` — stop accepting a material at a branch; also closes its open rate
- `GET /collection-points/{id}/materials` — accepted materials + current rate (the eventual public-site source of truth)
- `GET /collection-points/{id}/materials/{material_id}/rate-history` — full rate history for that branch/material

Every admin write (material/point created or updated, rate changed, acceptance added or removed) writes an `audit_log` row — `backend/app/services/audit_service.py`.

Verified against the real database: creating a material, accepting it at a branch, changing its rate, and confirming the rate history shows the old row closed out and the new one open — not asserted against a mock, the actual Postgres rows.

## Inventory ledger (Phase 5, done)

`backend/app/services/inventory_service.py` — the actual correctness centerpiece of this project (§11). No routes yet, deliberately: this is internal service infrastructure that Phase 6 (collection transactions) and Phase 9 (dashboards) will call, built and proven correct first.

`post_movement(...)` appends one immutable `inventory_ledger` row and updates `inventory_summary` in the same DB transaction — never a read-then-write. It does **not** commit; the caller (e.g. a future "record a collection" endpoint) composes it into a larger transaction alongside whatever else needs to succeed or fail atomically.

**A real bug found and fixed while building this, not assumed away**: the first version used `INSERT ... ON CONFLICT DO UPDATE` for the atomic increment. Postgres validates a `CHECK` constraint against that statement's raw `VALUES` tuple during its speculative-insert phase — *before* it even knows a conflict exists — so a valid negative delta (e.g. a correction on top of a healthy balance) could be wrongly rejected as if it were a fresh negative starting balance. Reproduced against a throwaway table to confirm it was genuine Postgres behavior before changing anything. Fixed by trying a plain atomic `UPDATE` first (whose `CHECK` validation runs against the real computed row) and only falling back to `INSERT` — inside a `SAVEPOINT` to keep a lost race retryable — when no row exists yet.

`backend/tests/test_inventory_service.py` proves, against the real database:
- sequential collections accumulate correctly and the ledger sums to the summary balance
- an adjustment can correctly reduce a healthy balance (the exact case the bug above broke)
- an adjustment that would push the balance negative is rejected and leaves no partial trace
- **20 concurrent threads, each its own DB connection, each posting +1 at the same instant, produce a final balance of exactly 20** — the actual claim this whole design rests on, proven against real concurrent Postgres connections, not asserted in a single-threaded test that couldn't have caught a race even if one existed

## Collection transactions (Phase 6, done)

`POST /api/v1/collection-transactions` — staff-only (§06: admin can view, never record), always at the staff member's own branch, never a point the client supplies. Online-only for now; Phase 8 adds the offline outbox on top without changing this endpoint's contract.

What it actually does, in one DB transaction: looks up the branch's *current* rate for the material (rejects with 409 if that material isn't accepted there), inserts the immutable `collection_transaction` row, then calls Phase 5's `inventory_service.post_movement(...)` to post exactly one ledger entry and update the summary — both succeed or both roll back together.

**Idempotency (§10) is real, not aspirational**: `client_transaction_uuid` is a required client-generated field even in this online-only phase, so the contract never has to change when Phase 8's offline outbox starts generating it on a device instead of a browser tab. Submitting the same UUID twice returns the *original* record as a 200-equivalent success, not an error — and, proven by test, does not double-count the inventory.

Fixed one real bug while writing the tests (not application code — a test fixture ordering bug, but worth noting because it's the same category of mistake the app itself is designed to prevent): a teardown fixture deleted a staff `user` row while a `collection_transaction` still referenced it via `recorded_by_user_id`, violating the FK, because fixtures tear down in reverse dependency order and the transaction cleanup lived in the wrong fixture. Moved it to the fixture that actually owns that foreign key.

`backend/tests/test_collection_transactions.py` proves, against the real database: only staff (never admin) can record; a duplicate `client_transaction_uuid` is idempotent and does not double-count; recording against a material the branch doesn't accept is rejected; staff can't view another branch's transactions; admin can view all. 29/29 backend tests pass.

## Payments (Phase 7, done)

`POST/GET /api/v1/collection-transactions/{id}/payments` — staff-only to record (same branch-scoping as recording the collection itself), admin can view. Manual recording only, per §25 item 2 — no live M-Pesa/Daraja disbursement. A transaction can have more than one payment (§08: the FK is one-to-many), so this never enforces "already paid," it just records what staff report happened.

One rule enforced beyond the bare minimum: an M-Pesa payment must include a reference number (the confirmation code) — cash doesn't need one. Without that, "recorded which method was used" would be true in name only for the one method where a real, checkable reference always exists.

`backend/tests/test_payments.py` proves, against the real database: only staff can record (admin is blocked), M-Pesa without a reference is rejected, cash without one is fine, a transaction can carry multiple payments, and a staff member can't pay against another branch's transaction. 36/36 backend tests pass.

## Offline-first collection app (Phase 8, done)

This is the centerpiece — everything else in this build exists to support this phase's claim: recording a collection works correctly whether the device is online, offline, or drops mid-sync.

**Backend**: `POST /api/v1/sync/collection-transactions` (`backend/app/services/sync_service.py`) takes a batch of items and processes each one independently through the *same* `collection_transaction_service.record_collection` path Phase 6's direct endpoint uses — one item's failure (e.g. a stale material reference) is caught, rolled back, and reported as `"conflict"`, without affecting any other item in the batch. Proven by test: a 3-item batch with a deliberately bad middle item returns `synced, conflict, synced` and the ledger reflects only the two good ones.

**Frontend** (`apps/collection-app`): a real login (session persisted via the rotating refresh token, §14/ADR-04), a collection-recording form, and a Dexie/IndexedDB outbox with a visible sync-status panel (`backend`'s claims are only worth something if a person can *see* pending vs. synced, not just trust that it works):

- `src/db.ts` — the outbox (one row per collection, keyed by the same `client_transaction_uuid` the backend uses for idempotency) and a reference cache of the branch's accepted materials, so the form works fully offline once loaded once.
- `src/sync.ts` — the engine: drains the outbox on an `online` event, a 30s timer, and a manual "Sync now" button (never relying on the unreliable-cross-browser Background Sync API alone, per §10). A dropped request puts everything back to `pending` rather than leaving it stuck.
- `src/CollectionForm.tsx` / `src/OutboxStatus.tsx` — recording and visibility, reactive via `dexie-react-hooks` so the UI updates the instant the sync engine changes a row's status.

**Verified live, not just unit-tested** — a real Playwright-driven Edge browser hitting the real dev servers, doing exactly the demo script from §10/§26:
1. Log in, submit a collection online → shows **Synced** within moments.
2. Real network-level offline (Playwright's `context.setOffline(true)`, not a mock) → UI correctly shows "offline".
3. Submit a second collection while offline → queues as **Pending**, does not fail or hang.
4. Reconnect, click **Sync now** → the queued item transitions to **Synced** — both records end up correct in the real Postgres ledger.

One real bug fixed along the way (not assumed away): the offline-submit test generated two different UUIDs — one for the outbox row's key, one inside its payload — which would have silently broken the idempotency guarantee the whole design rests on. Caught before it shipped by tracing through the code, not by a failing test.

`backend/tests/test_sync.py` (4 tests) covers the server side; the interactive script above covers the actual user-facing claim end to end.

## Admin portal & dashboards (Phase 9, done)

`GET /api/v1/inventory/summary` (new) joins Phase 5's ledger-backed balances with material names for display, scoped the same way as everything else (admin sees all branches, staff their own). The existing `GET /collection-transactions` gained an `on_date` filter for "today's collections."

`apps/admin-portal` now does something: real login (shared with collection-app — see below), a branch/date filter, a current-inventory table, and a today's-collections table. Deliberately still "thin" per §22 — no charts, no aggregates beyond what these two tables show.

**Real duplication got resolved, not left to rot**: by Phase 9, both frontend apps needed the identical login flow. Rather than copy-pasting `auth.tsx`/`LoginForm.tsx` a second time, they moved into `packages/ui` — the package that existed since Phase 1 for exactly this and had sat empty until now. `@takaflow/api-client` and `@takaflow/types` grew the remaining read endpoints (`listCollectionPoints`, `listInventorySummary`, `listCollectionTransactions`).

Verified live: real admin login against real data (two collection transactions, 4kg + 6kg) — the dashboard correctly shows 10kg on hand, resolves the branch's actual name rather than a raw ID, and lists both transactions for the day, including the "walk-in" label surfacing the no-supplier-registration decision (§25 item 7) directly in the UI. `backend/tests/test_inventory_summary.py` (3 tests) covers the scoping and date-filter logic; 43/43 backend tests pass overall.

## MVP complete (§22)

Every must-have item from the blueprint's MVP list is built and verified: auth/RBAC, materials & branches, walk-in collection transactions, the inventory ledger, offline-first sync, manual payments, and the thin admin view. Predictive analytics, the buyer portal, and live M-Pesa disbursement remain out of scope per §22/§25 — deliberately, not by omission.

## Public site (Phase 12, done)

`apps/public-site` — no login, no `packages/ui` dependency (it has no session to manage), reading two new unauthenticated endpoints: `GET /api/v1/public/collection-points` (active branches only) and `GET /api/v1/public/collection-points/{id}/materials` (accepted materials + current rate — the same rate data staff see, since advertising "we pay X/kg here" to walk-in collectors is the actual point of a public site for this business). A deactivated branch's materials endpoint 404s the same way a nonexistent one would, rather than leaking a closed branch's details.

**A real leftover found and fixed while checking the live page, not left for someone else to notice**: the demo page initially showed a stray "Debug Point" with address "x" — a row created by a one-off reproduction script back in Phase 5 (the `INSERT ... ON CONFLICT` investigation) whose cleanup code never ran because the script deliberately crashed to reproduce the bug. It had been sitting in the dev database, invisible, until this was the first phase to publicly list *every* active collection point. Removed it, then swept every collection point/material/user row in the database to confirm nothing else from earlier phases' manual testing had leaked through.

Verified live: real branch data (name, address, opening hours) and a real rate (15.5/kg) rendered with no authentication at all. `backend/tests/test_public.py` (5 tests) covers the no-auth access, the active-only filter, and the inactive-branch 404. 48/48 backend tests pass.

## Optional next steps

Nothing left is architecturally required. Phases 10 (buyer portal), 11 (matching & transfers), and 13 (predictive analytics) stay out of scope per §22/§25 — deliberately dropped for this timeline, not forgotten. What's left is hardening and packaging:
- **Testing hardening** (§21 Phase 14) — the test suite already covers each phase's own correctness claims; a pass looking specifically for gaps *across* phases (e.g. what happens to a payment if its transaction's material is later deactivated) would be the highest-value use of remaining time.
- **Deployment** (§21 Phase 15) — standing up the free-tier hosting from §20 so the app is reachable outside `localhost` for the defense.
