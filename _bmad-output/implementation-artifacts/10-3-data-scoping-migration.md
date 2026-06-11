# Story 10.3: Data Scoping Migration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Source of truth: Epic 10 was NOT added to epics.md, and prd.md/architecture.md were NOT amended.
     This story is built from the Sprint Change Proposal (authoritative spec for Epic 10) + Story 10.1
     (User model + gate) + Story 10.2 (per-user identity/token/login) + direct codebase analysis. See References. -->

## Story

As a **Spotify user of the multi-tenant deployed app**,
I want **the playlists I select, the tracks I blacklist, my sync history, and my settings to belong only to me**,
so that **I see and act on only my own data — never the owner's or another user's — and existing production data is preserved by being assigned to the owner instead of lost**.

## Context & Scope Boundary (READ FIRST)

This is the **multi-tenant correctness** story of Epic 10. Stories 10.1 → 10.2 made **identity and tokens** per-user (the `User` table, sessions, the auth gate, per-user OAuth/token, login/logout). But **every data row and every setting is still global**: `Playlist`, `track_blacklist`, `sync_log` have no owner, and the per-user settings (`playlist_size`, `cron_expr`, dynamic-playlist id, `last_sync_at`) still live on the single global `Config` row. **10.3 closes that gap**: it scopes the data tables and migrates the settings onto `User`. Per Story 10.1/10.2's notes, **10.1 → 10.2 → 10.3 are designed to ship together** — full multi-tenant correctness arrives here.

**IN SCOPE (10.3):**
- **Schema:** add `user_id` (FK → `user.id`) to `Playlist`, `track_blacklist`, `sync_log`. Change `Playlist` uniqueness from **global** `spotify_id` to **per-user** `(user_id, spotify_id)`. Change `track_blacklist` PK from `spotify_id` to a **composite** `(user_id, spotify_id)` (two users may blacklist the same track). Add `last_sync_at` to `User` (the only settings column 10.1 did not pre-create — `playlist_size`/`cron_expr`/`target_playlist_id` already exist on `User`).
- **One-shot idempotent migration (no Alembic — AR8):** `create_all()` does NOT alter existing tables, so a startup migration must `ALTER TABLE`/rebuild the existing prod tables, then **backfill** every orphaned `Playlist`/`track_blacklist`/`sync_log` row to the **owner** (the single/first `User`), and **migrate the `Config` settings** (`playlist_size`, `cron_expr`, `dynamic_playlist_id`→`target_playlist_id`, `last_sync_at`) onto that owner `User`. Idempotent and a no-op on a fresh install (where `create_all` already builds the correct schema).
- **Query scoping:** every DB query touching `Playlist`/`track_blacklist`/`sync_log` is filtered by `current_user.id`; every write stamps `user_id = current_user.id`. This includes routers that currently take **no** `current_user` (`toggle_playlist`, the whole `blacklist` router, `get_sync_logs`/`get_sync_status`) — they gain `CurrentUserDep`.
- **Settings move off `Config` onto `User`:** `routers/config.py` reads/writes the **current user's** settings; `services/spotify.py` dynamic-playlist read/write uses `user.target_playlist_id`; `services/sync_engine.py` + the `sync/stream` SSE read `playlist_size`/`last_sync_at` from the user and write `last_sync_at` back to the user.
- **`blacklist_service.get_blacklisted_ids(session)` → `get_blacklisted_ids(session, user_id)`** (filtered by user).
- **Scheduler bridge stays single-job (defer to 10.4):** the global job + lifespan bootstrap now source `cron_expr` from the **owner** `User` (via the existing `_resolve_scheduled_user()` bridge) instead of `Config`. Tag `# TODO(10.4)`.
- **Tests:** new `test_story_10_3.py` (per-user isolation across all four concerns + migration/backfill); repair existing router/service tests for the new `user_id` columns, scoped queries, and `get_blacklisted_ids` signature.

**EXPLICITLY OUT OF SCOPE — do NOT implement here:**
- **Per-user scheduler jobs** (`sync_{user_id}`, one APScheduler job per user) → **Story 10.4**. 10.3 keeps the single global job, just sourced from the owner user's `cron_expr`. Multi-user cron correctness is 10.4's problem.
- **Prod hardening** (redirect URI registration, Secure/HttpOnly cookie verification in prod, returning-user end-to-end) → **Story 10.5**.
- Re-litigating identity/token/login — that is done (10.1/10.2). Do not touch the login round-trip, `SQLiteCacheHandler`, or `_get_spotify_oauth`.

**Default design decision (committed; flagged as Open Question #1):** after the migration reads it, the legacy global `Config` **model is removed** and `routers/config.py` becomes a per-user *settings* router operating on `current_user`. The migration reads the old `config` **table** via raw SQL (the table is left physically in place as a backup; it is NOT dropped). If you disagree, the fallback is to keep `Config` dormant — but the codebase must then never read/write it again.

## Acceptance Criteria

1. **Data tables carry an owner.** `Playlist`, `track_blacklist`, and `sync_log` each have a `user_id` column that is a foreign key to `user.id` and is indexed. Newly written rows in any of the three are stamped with the writing user's `id`.

2. **Per-user uniqueness, not global.** Two different users can each have a `Playlist` row with the same `spotify_id`, and can each blacklist the same track `spotify_id`, without collision. `Playlist` enforces uniqueness on `(user_id, spotify_id)` (the old global `spotify_id` unique constraint is gone); `track_blacklist`'s primary key is the composite `(user_id, spotify_id)`.

3. **Settings live on `User`.** `User` has a `last_sync_at` column (ISO-8601 string, nullable). The current user's `playlist_size`, `cron_expr`, `target_playlist_id` (the dynamic "Recent Adds" playlist id), and `last_sync_at` are read from and written to that user's `User` row — never the global `Config` row.

4. **One-shot migration preserves and backfills prod data.** On startup, a single idempotent migration runs (before/around `create_all`) that: (a) adds `user_id` to the three tables and reshapes the uniqueness/PK per AC#2 on the **existing** SQLite tables; (b) assigns every pre-existing `Playlist`/`track_blacklist`/`sync_log` row to the **owner** (the single/first `User` row); (c) copies the old `Config` settings (`playlist_size`, `cron_expr`, `dynamic_playlist_id`→`target_playlist_id`, `last_sync_at`) onto the owner `User`. Running it a second time changes nothing (idempotent). On a fresh DB (no legacy tables/rows, no users), it is a safe no-op and the app still boots.

5. **Every read is scoped to the current user.** `GET /playlists` lists/upserts/prunes only the current user's `Playlist` rows; `PATCH /playlists/{id}` and `GET /playlists/{id}/tracks` only touch the current user's data; `GET /blacklist` returns only the current user's blacklist; `GET /sync/logs` and `GET /sync/status` return only the current user's logs; `GET /recently-added` reflects the current user's dynamic playlist. A row owned by user A is never visible to or mutable by user B.

6. **Every write is scoped to the current user.** `PATCH /playlists/{id}` updating a `spotify_id` that belongs to another user returns **404** (not found *for this user*), not a cross-tenant mutation. `POST /blacklist` / `DELETE /blacklist/{id}` create/delete only within the current user's scope. Manual sync (`POST /sync/run` is global-scheduler-path; `GET /sync/stream` is request-scoped) writes `sync_log` rows and `last_sync_at` against the acting user.

7. **`blacklist_service.get_blacklisted_ids` is user-scoped.** Its signature becomes `get_blacklisted_ids(session, user_id)` and it returns only that user's blacklisted ids. All callers (`services/spotify.py` ×3, `services/sync_engine.py`) pass the resolved user's id.

8. **Dynamic playlist is per-user.** `get_or_create_dynamic_playlist`, `_persist_dynamic_playlist_id`, `get_user_playlists`, and `get_recently_added_tracks` read/write the dynamic playlist id from `user.target_playlist_id`, not `Config.dynamic_playlist_id`. Each user gets/creates their own "Recent Adds" playlist.

9. **Settings endpoints operate on the current user.** `GET /config` returns the current user's `playlist_size`/`cron_expr`/`target_playlist_id` (mapped to the existing `dynamic_playlist_id` response field) with `setup_required` derived from the current user (a logged-in user always has credentials → `setup_required: false`). `PATCH /config` updates the current user's `playlist_size`/`cron_expr` and re-bootstraps the scheduler from the user's `cron_expr`. **The GET/PATCH `/config` response and request JSON shapes are unchanged** (snake_case, same field names) so the existing frontend keeps working without edits.

10. **Scheduler bridge sources cron from the owner user.** The lifespan bootstrap and `PATCH /config` bootstrap the single global `sync_job` from the owner/current user's `cron_expr` (via the `_resolve_scheduled_user()` bridge), tagged `# TODO(10.4)`. No `Config.cron_expr` read remains. (Per-user jobs are 10.4.)

11. **`Config` is no longer read or written by application code.** No router or service reads/writes the `Config` model after the migration (the migration may read the old `config` **table** via raw SQL). Per the default decision, the `Config` model is removed from `models/__init__.py` and imports.

12. **No token/secret leakage; conventions preserved.** No new endpoint or response exposes `client_secret`/`client_id`/`token_json`/tokens (NFR5). JSON stays snake_case, arrays returned directly (no `{"data": …}`), business logic stays in `services/` not routers, all spotipy calls go through `services/spotify.py`.

13. **Full suite green; new behavior covered.** `test_story_10_3.py` proves per-user isolation for playlists, blacklist, sync logs, and settings, plus the migration/backfill (legacy rows → owner; `Config` settings → owner `User`) and idempotency. All pre-existing tests pass after being updated for the `user_id` columns, scoped queries, and the `get_blacklisted_ids(session, user_id)` signature. Run via Docker only.

14. **Postman updated.** Any route whose contract changed in 10.3 (scoping is transparent, but `/config` now operates per-user; confirm `/blacklist`, `/sync/logs`, `/playlists` descriptions note per-user scoping) is updated in the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`) and verified via a follow-up GET.

## Tasks / Subtasks

- [x] **Task 1: Schema — add `user_id` + reshape uniqueness/PK** (AC: #1, #2, #3)
  - [x] `backend/models/user.py`: add `last_sync_at: Optional[str] = None`.
  - [x] `backend/models/playlist.py`: add `user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)`. Remove `unique=True` from `spotify_id`. Add `__table_args__ = (UniqueConstraint("user_id", "spotify_id"),)` (import `UniqueConstraint` from `sqlalchemy`).
  - [x] `backend/models/track_blacklist.py`: make PK composite — `spotify_id: str = Field(primary_key=True)` **and** `user_id: int = Field(foreign_key="user.id", primary_key=True, index=True)`. (SQLModel supports multi-column PK via two `primary_key=True` fields.) Keep `blacklisted_at`.
  - [x] `backend/models/sync_log.py`: add `user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)`.
  - [x] Verify `create_all` builds the correct fresh schema for all four (it is only used for fresh installs / tests; existing prod tables are handled by Task 2).

- [x] **Task 2: One-shot idempotent migration + backfill** (AC: #4)
  - [x] Create `backend/migrations.py` with a single `run_migrations(engine)` function, called from `main.py` lifespan **before** `SQLModel.metadata.create_all(engine)` is NOT enough on its own — call `run_migrations` right after `create_all` so new tables exist, then reshape/backfill existing ones. (Order: `create_all` first to guarantee `user` table exists; then `run_migrations` to patch the legacy data tables and backfill.)
  - [x] **Idempotency guard:** use `PRAGMA table_info(<table>)` to detect whether `user_id` already exists; skip per-table work that's already done. Use `try/except`/`IF NOT EXISTS` defensively. The migration must be safe to run on every boot.
  - [x] **`playlist` + `sync_log`:** `ALTER TABLE … ADD COLUMN user_id INTEGER` if missing. For `playlist`, drop the old global unique index on `spotify_id` (find its name via `PRAGMA index_list(playlist)`; `DROP INDEX` it) and create the composite unique index `CREATE UNIQUE INDEX IF NOT EXISTS ix_playlist_user_spotify ON playlist(user_id, spotify_id)`. Add `CREATE INDEX IF NOT EXISTS` on `user_id` for both.
  - [x] **`track_blacklist` (PK change needs a table rebuild — SQLite can't alter a PK in place):** if the legacy single-column-PK shape is detected, create a new table with composite PK `(spotify_id, user_id)`, `INSERT … SELECT` existing rows (assigning the owner id), `DROP TABLE track_blacklist`, `ALTER TABLE … RENAME`. Guard the whole rebuild behind the idempotency check.
  - [x] **Resolve the owner** = the single/first `User` row (mirror `sync_engine._resolve_scheduled_user`). If there is **no** user yet (fresh deploy that hasn't logged in), skip backfill — there is nothing to own the rows and `create_all` already made the schema correct; the migration is a no-op.
  - [x] **Backfill:** `UPDATE playlist SET user_id = :owner WHERE user_id IS NULL`; same for `track_blacklist` (handled by the rebuild INSERT) and `sync_log`.
  - [x] **Migrate settings:** read the legacy `config` table via **raw SQL** (`SELECT playlist_size, cron_expr, dynamic_playlist_id, last_sync_at FROM config LIMIT 1`, guarded by a table-exists check). Copy onto the owner `User`: `playlist_size`, `cron_expr`, `target_playlist_id ← dynamic_playlist_id`, `last_sync_at`. Only overwrite `User` fields that are still at their defaults/None so re-runs don't clobber user-edited settings (idempotency).
  - [x] Do **NOT** `DROP TABLE config` — leave it physically as a backup. The model is removed in Task 6.

- [x] **Task 3: Scope the routers by `current_user`** (AC: #5, #6, #12)
  - [x] `routers/playlists.py`:
    - `get_playlists`: scope the existing-row `select` to `.where(Playlist.user_id == current_user.id, Playlist.spotify_id == p["spotify_id"])`; stamp `user_id=current_user.id` on inserts; scope the "prune deleted" `select(Playlist)` and the final read `select(Playlist)` to `.where(Playlist.user_id == current_user.id)`.
    - `toggle_playlist`: **add `current_user: CurrentUserDep`** and scope the lookup `.where(Playlist.user_id == current_user.id, Playlist.spotify_id == spotify_id)` → 404 if not this user's.
    - `get_playlist_tracks` already passes `current_user` to the service — no scoping change needed there beyond Task 4's blacklist filter.
  - [x] `routers/blacklist.py`: add `current_user: CurrentUserDep` to all three endpoints; `GET` filters by `user_id`; `POST` checks existence within `(user_id, spotify_id)` and writes `user_id=current_user.id`; `DELETE` scopes by `(user_id, spotify_id)`.
  - [x] `routers/sync.py`: `get_sync_logs` and `get_sync_status` gain `current_user: CurrentUserDep` and filter `select(SyncLog).where(SyncLog.user_id == current_user.id)`. The `sync/stream` SSE already receives `current_user` — thread its `id` into the scoped `Playlist`/`SyncLog`/`last_sync_at` reads/writes (Task 5).

- [x] **Task 4: Scope blacklist service + spotify service** (AC: #7, #8, #12)
  - [x] `services/blacklist_service.py`: `get_blacklisted_ids(session, user_id: int)` → `select(TrackBlacklist).where(TrackBlacklist.user_id == user_id)`.
  - [x] `services/spotify.py`:
    - `get_playlist_tracks_full`, `get_playlist_tracks_page`, `get_recently_added_tracks`: pass `current_user.id` to `get_blacklisted_ids(session, user.id)` (they already receive `user`).
    - Dynamic playlist: replace all four `Config.dynamic_playlist_id` reads/writes with `user.target_playlist_id`. Change signatures: `get_or_create_dynamic_playlist(sp, user)`, `_persist_dynamic_playlist_id(playlist_id, user)`; `get_user_playlists(user)` reads `user.target_playlist_id`; `get_recently_added_tracks(user)` reads `user.target_playlist_id`. Persist a newly-created/adopted dynamic id onto `user.target_playlist_id` (load the `User` row in a `Session` and commit, mirroring the old `_persist_dynamic_playlist_id`).
  - [x] Remove the `from models.config import Config` import from `services/spotify.py` once no Config reads remain.

- [x] **Task 5: Settings off `Config` onto `User` + sync engine/stream** (AC: #3, #9, #10)
  - [x] `routers/config.py`: inject `current_user: CurrentUserDep` on `GET`/`PATCH`. `GET /config`: `setup_required = not bool(current_user.client_id)` (a session user has creds → false), return `current_user.playlist_size`/`cron_expr`/`target_playlist_id` (as the `dynamic_playlist_id` field). `PATCH /config`: update `current_user.playlist_size`/`cron_expr`, validate cron, commit, `bootstrap_scheduler(current_user.cron_expr)` on cron change. **Remove `PUT /config`** (credentials now flow through `/auth/connect` — vestigial since 10.2) and the `ConfigWrite` model, OR keep `PUT` but point it at `current_user` — default: **remove it** (flag as Open Question #2). Drop the `from models.config import Config` import.
  - [x] `services/sync_engine.py`: in `run_sync`, read `playlist_size`/`last_sync_at` from the resolved `user` (not `Config`); write `last_sync_at` back to that `User` row; scope the `select(Playlist)` to `.where(Playlist.user_id == user.id, …)`; pass `user.id` to `get_blacklisted_ids`; stamp `user_id=user.id` on the `SyncLog` write (thread `user_id` into `_write_sync_log`). `get_or_create_dynamic_playlist(sp, user)`.
  - [x] `routers/sync.py` `_run_sync_stream(current_user)`: read `playlist_size`/`last_sync_at` from `current_user`; scope `Playlist` query to `current_user.id`; write `last_sync_at` to the `current_user` row; `get_or_create_dynamic_playlist(sp, current_user)`; `_write_sync_log(..., user_id=current_user.id)`. Remove the `from models.config import Config` import here.
  - [x] `main.py` lifespan: replace the `Config.cron_expr` read with `_resolve_scheduled_user()` → `user.cron_expr` (None if no user). Tag `# TODO(10.4): per-user scheduler jobs`.

- [x] **Task 6: Remove the `Config` model** (AC: #11) — *default decision; see Open Question #1*
  - [x] After Tasks 3–5 leave zero `Config` model reads/writes in app code, remove `from .config import Config` and `"Config"` from `backend/models/__init__.py`, and delete (or keep but unreferenced) `backend/models/config.py`. Do NOT drop the physical `config` table (Task 2 backup). Grep the whole `backend/` tree for `Config` to confirm no stray import (except `migrations.py` raw-SQL, which references the table name as a string, not the model).

- [x] **Task 7: Tests** (AC: #13)
  - [x] New `backend/tests/test_story_10_3.py`: (a) two users each select the same `spotify_id` playlist → no unique collision, each `GET /playlists` shows only their own; (b) user A's `PATCH /playlists/{id}` on a `spotify_id` owned only by B → 404; (c) two users blacklist the same track id → both rows coexist (composite PK), each `GET /blacklist` shows only their own, `DELETE` scoped; (d) `GET /sync/logs`/`/status` per-user; (e) settings: `PATCH /config` for user A doesn't change user B's `playlist_size`/`cron_expr`; `GET /config` reads the current user's settings; (f) `get_blacklisted_ids(session, user_id)` isolation; (g) dynamic playlist id stored on `user.target_playlist_id` per-user; (h) **migration**: seed a legacy DB (raw-SQL `config` row + orphaned `playlist`/`track_blacklist`/`sync_log` rows with no `user_id` + one owner `User`), run `run_migrations`, assert rows backfilled to owner and `Config` settings copied onto owner `User`; (i) **idempotency**: run `run_migrations` twice → no change/no error; (j) fresh-DB no-op (no users) boots cleanly.
  - [x] Update existing router/service test fixtures: they already inject `User(id=1, spotify_user_id="test_user")` via `app.dependency_overrides[get_current_user]` (10.1). Now also **seed that same user row into the session** (so FK + scoped queries resolve) and stamp `user_id=1` on any pre-seeded `Playlist`/`TrackBlacklist`/`SyncLog` test rows. Fix the `get_blacklisted_ids(session, user_id)` callers in `test_story_8_5` and any blacklist/playlist/sync tests. The sync-engine test fixtures (`test_story_3_3`, `3_4`, `8_5`) already seed a `User` (10.2) — extend them to set `user.playlist_size`/`cron_expr` instead of a `Config` row where they relied on `Config`.
  - [x] Run the FULL suite: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`. Expect fallout in every test that built a `Config` row for settings or assumed global tables — migrate them to per-user `User` settings + `user_id`-stamped rows.

- [x] **Task 8: Postman + docs** (AC: #14)
  - [x] Update the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`): note per-user scoping on `/playlists`, `/blacklist`, `/sync/logs`, `/recently-added`; `/config` now per-user (remove `PUT /config` if it was documented); GET/PATCH `/config` shapes unchanged. Verify via a follow-up GET.

## Dev Notes

### Authoritative spec & how 10.3 fits
- **Source of truth = the Sprint Change Proposal** (Epic 10 was never written into `epics.md`; PRD/architecture were not amended). Story 10.3 = proposal **§4.3 "10.3"** + the data-model/token lines in **§2.3**/**§4.2**.
- §4.3 line: *"10.3 — Data scoping migration: add `user_id` to `Playlist`/`track_blacklist`/`sync_log`; backfill existing prod rows to the owner; filter every query by current user."*
- §2.3 (architecture conflicts): *"`Playlist`, `track_blacklist`, `sync_log` each gain a `user_id` FK"* and *"SQLModel auto-create (AR8, no Alembic) — adding `user_id` to existing tables with live prod data is not handled by `create_all()`. A one-shot migration/backfill (assign existing rows to the owner) or a dev-data reset is required."*
- §4.2: *"`Playlist`, `track_blacklist`, `sync_log`: add `user_id` FK; all queries filtered by current user."* and the data-migration bullet: *"create a `User` row for the existing owner, backfill `user_id` on existing rows."*
- **The settings migration is the half 10.2 explicitly deferred here.** Story 10.2 §"Settings stay on `Config` in 10.2": *"migrating the per-user settings (`dynamic_playlist_id`, `playlist_size`, `cron_expr`, `last_sync_at`) off the global `Config` row onto `User` → Story 10.3. The `User` model has its own `playlist_size`/`cron_expr`/`target_playlist_id` columns (added in 10.1) but they are dormant until 10.3 migrates settings onto them. Do not wire them up here — that drags 10.3 in."* → **10.3 wires them up.**

### What 10.1/10.2 already built (do NOT redo)
- **10.1:** `User` model (with dormant `playlist_size`/`cron_expr`/`target_playlist_id`), `SessionMiddleware`, `get_current_user`/`CurrentUserDep`, the 401 auth gate on the 5 business routers (`config`, `playlists`, `sync`, `blacklist`, `recently_added`). 15 router-test fixtures already override `get_current_user`.
- **10.2:** per-user token (`SQLiteCacheHandler(user_id)` → `User.token_json`), per-user OAuth (`_get_spotify_oauth(user)`, `get_authenticated_client(user)`), the `state`-protected login round-trip (`start_login`/`complete_login`), session-based `/auth/status`, `current_user` threaded through `playlists`/`recently_added`/`sync` stream, the `_resolve_scheduled_user()` scheduler bridge, frontend `LoginScreen` + cookies + logout. **Identity & token are per-user; data rows & settings are still global — that is exactly what 10.3 fixes.**
- `User.target_playlist_id` is the 10.1-created analog of `Config.dynamic_playlist_id`. `User` does **not** have `last_sync_at` yet — 10.3 adds it (Task 1).

### The migration is the riskiest part — get it exactly right
- **No Alembic (AR8).** SQLite via `SQLModel.metadata.create_all(engine)` in `main.py` lifespan. `create_all` **only creates missing tables** — it never alters an existing table's columns/constraints. So adding `user_id` and changing the `track_blacklist` PK on the **live prod DB** (`sqlite:////data/app.db`) MUST be done by an explicit migration.
- **SQLite ALTER limits:** `ADD COLUMN` is supported; **dropping/altering a PK or unique constraint is NOT** — you must rebuild the table (create-new → `INSERT … SELECT` → drop-old → rename). `playlist` only needs an index swap (drop old global unique index on `spotify_id`, add composite unique index) + `ADD COLUMN`. `track_blacklist` needs a **full rebuild** because its PK changes. `sync_log` only needs `ADD COLUMN`.
- **Idempotency is mandatory** (the lifespan runs on every boot): guard each step with `PRAGMA table_info(...)`/`PRAGMA index_list(...)` existence checks and `IF NOT EXISTS`. Re-runs must be no-ops.
- **Owner resolution:** the single/first `User` (same as `sync_engine._resolve_scheduled_user()`). **No user yet** (fresh deploy pre-login) → skip backfill entirely; `create_all` already produced the correct fresh schema, so the migration is a safe no-op and the app boots.
- **Settings copy is also idempotent:** only overwrite owner `User` fields that are still default/None, so a second run (or a user who already edited settings post-migration) isn't clobbered.
- **Run order in lifespan:** `create_all(engine)` first (ensures `user` table exists for FK + fresh-install schema), then `run_migrations(engine)` (patches legacy data tables + backfills + settings copy), then start the scheduler bootstrapped from the owner user's `cron_expr`.

### Query-site inventory (every place that must be scoped — do not miss one)
Found via grep; scope each by `user_id`:
- `routers/playlists.py`: lines ~57 (existing select), ~66 (prune select), ~73 (final read), ~118 (`toggle_playlist` select — **and add `current_user`**).
- `routers/blacklist.py`: lines ~24, ~37, ~59 (all three endpoints — **add `current_user`**).
- `routers/sync.py`: lines ~18, ~26 (`get_sync_logs`/`get_sync_status` — **add `current_user`**), ~61 (`_run_sync_stream` Playlist select), ~66/~95 (`Config` reads → `current_user` settings).
- `services/sync_engine.py`: line ~88 (Playlist select), ~93/~125 (`Config` reads/writes → owner `User`), ~96 (`get_blacklisted_ids`), `_write_sync_log` (stamp `user_id`).
- `services/spotify.py`: lines ~170, ~214, ~251, ~518 (`Config` reads/writes → `user.target_playlist_id`); `get_blacklisted_ids` calls at ~400, ~460, ~520.
- `services/blacklist_service.py`: line ~12 (`get_blacklisted_ids` — add `user_id` filter).
- `routers/config.py`: lines ~40, ~58, ~81 (`Config` reads/writes → `current_user`).
- `main.py`: line ~26 (`Config.cron_expr` lifespan read → owner `User`).

### Scheduler stays single-job until 10.4 (intentional bridge)
The APScheduler job is still **one global `sync_job`** (`scheduler.py` `bootstrap_scheduler`). 10.3 does NOT create per-user jobs. It only changes the **source** of the cron from `Config.cron_expr` to the owner user's `cron_expr` (via `_resolve_scheduled_user()`), keeping the single-job bridge `_resolve_scheduled_user()` that 10.2 introduced for the run. When multiple users have different `cron_expr` values, only the owner's wins — that incorrectness is **explicitly 10.4's job** (per-user jobs `sync_{user_id}`). Tag every bridge touchpoint `# TODO(10.4)`.

### Frontend: no change required (contract preserved)
The frontend consumes `/config` via `useConfig` → `ConfigForm` (PATCH `playlist_size`/`cron_expr`) and `RecentlyAddedPage` (`dynamic_playlist_id`, `playlist_size`). 10.3 keeps the **GET/PATCH `/config` JSON shapes identical** (same snake_case fields), so these work unchanged. `setup_required` is now derived per-user (always `false` for a session user, since login guarantees creds) — the frontend already handles `false` (it only showed setup when `true`, which the gated `/config` will no longer return). The `PUT /config`/`ConfigWrite` path (`useUpdateConfig`) became dead in 10.2 (LoginScreen posts to `/auth/connect`); if you remove `PUT /config` (Task 5), also delete the dead `useUpdateConfig` mutation + `ConfigWrite` type in `frontend/src/hooks/useConfig.ts` / `types/index.ts` — but verify `npm run build` (Node 22) still passes. This is optional cleanup, not behavior change.

### Testing standards (match the repo)
- Tests ONLY via Docker: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`.
- Fixture pattern (canonical: `test_story_9_1.py`): in-memory SQLite + `StaticPool`, `create_all`, `session` fixture, `client` fixture overriding `get_session` (and `get_current_user` for gated routes). Clear `app.dependency_overrides` on teardown.
- **New wrinkle for 10.3:** scoped queries + FKs mean the overridden `User(id=1, spotify_user_id="test_user")` must **also be persisted into the test session** (`session.add(user); session.commit()`), and any pre-seeded `Playlist`/`TrackBlacklist`/`SyncLog` test rows must carry `user_id=1`. Tests that previously built a `Config` row for settings switch to setting fields on the `User` row.
- **Migration tests:** create a raw engine, hand-build the *legacy* schema via raw SQL (old `config` table, `playlist`/`track_blacklist`/`sync_log` without `user_id`, one `User`), call `run_migrations(engine)`, and assert via raw SQL / model queries. Patch `services.spotify.engine` / `services.token_manager.engine` where the code under test uses the module-level engine (see `test_story_10_2.py` `client_fixture`).
- Service mocking: `patch("routers.<module>.spotify_service.<fn>", ...)`. Spotify mocked at the service boundary (`services.spotify.SpotifyOAuth`/`Spotify`). snake_case JSON, arrays returned directly.
- TDD order: write scoping + migration tests first (red), implement schema → migration → scoping → settings, then run the full suite and fix `Config`/signature fallout.

### Anti-patterns to avoid
- ❌ Do NOT rely on `create_all` to add `user_id` to existing tables — it won't; you MUST write the migration (Task 2).
- ❌ Do NOT make the migration non-idempotent — the lifespan runs it every boot; guard with `PRAGMA` checks.
- ❌ Do NOT `DROP TABLE config` — leave it as a backup; only stop reading the model.
- ❌ Do NOT build per-user scheduler jobs (`sync_{user_id}`) — that is 10.4. Keep the single global job sourced from the owner user.
- ❌ Do NOT forget the routers that currently take NO `current_user`: `toggle_playlist`, the whole `blacklist` router, `get_sync_logs`/`get_sync_status`. Unscoped, they leak/mutate across tenants.
- ❌ Do NOT change the GET/PATCH `/config` JSON shape — the frontend depends on it.
- ❌ Do NOT leave a global (unscoped) `select(Playlist)`/`select(TrackBlacklist)`/`select(SyncLog)` anywhere — grep to confirm every one is `.where(... .user_id == ...)`.
- ❌ Do NOT touch the login round-trip, `SQLiteCacheHandler`, `_get_spotify_oauth`, or token handling — done in 10.2.
- ❌ Do NOT expose `client_secret`/`token_json`/`client_id`/tokens in any response (NFR5).

### Project Structure Notes
- New: `backend/migrations.py` (one-shot `run_migrations(engine)`), `backend/tests/test_story_10_3.py`.
- Model edits: `backend/models/user.py` (`last_sync_at`), `backend/models/playlist.py` (`user_id` + composite unique), `backend/models/track_blacklist.py` (composite PK), `backend/models/sync_log.py` (`user_id`), `backend/models/__init__.py` (drop `Config`).
- Router edits: `backend/routers/playlists.py`, `backend/routers/blacklist.py`, `backend/routers/sync.py`, `backend/routers/config.py`.
- Service edits: `backend/services/blacklist_service.py`, `backend/services/spotify.py`, `backend/services/sync_engine.py`.
- App: `backend/main.py` (lifespan: call `run_migrations`, bootstrap cron from owner user). Possible delete: `backend/models/config.py`.
- Test edits: every router/service test that seeds settings/data rows (notably `test_story_3_1`, `3_2`, `3_3`, `3_4`, `3_5`, `5_*`, `7_1`, `8_*`, `9_*`, and the `2_4`/`config` tests). Optional frontend cleanup: `frontend/src/hooks/useConfig.ts`, `frontend/src/types/index.ts`.
- Conventions (CLAUDE.md): business logic in `services/` not routers; spotipy only via `services/spotify.py`; snake_case JSON; no response wrapper; tests Docker-only; Postman synced on API change; shadcn via CLI / Node 22 for any frontend touch.

### Open questions for the user (do not block implementation; flag in PR)
1. **Remove the `Config` model, or keep it dormant?** This story's default = remove the model (the migration reads the legacy `config` *table* via raw SQL; the table is kept as a backup, not dropped). Alternative: keep `Config` registered but never read/written. Default chosen: **remove**.
2. **`PUT /config`?** It became vestigial in 10.2 (credentials flow through `/auth/connect`). Default = **remove** `PUT /config` + `ConfigWrite` and the dead frontend `useUpdateConfig`. Alternative: keep it, repointed at `current_user`.
3. **Backfill vs dev-data reset?** The proposal allows either. Default = **backfill** prod rows to the owner (preserves data, the proposal's stated success criterion). A clean reset is only acceptable if the user confirms the prod data is disposable.
4. **Multi-user cron before 10.4:** with the single-job bridge, only the owner's `cron_expr` schedules. If a second user logs in and sets a different cron before 10.4 lands, their schedule won't run. Acceptable per the 10.3→10.4 split; surface it so it isn't a surprise.

### References
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.3] — Epic 10 story breakdown (10.3 = data scoping migration; 10.4 = per-user jobs).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.2] — `Playlist`/`track_blacklist`/`sync_log` gain `user_id`; settings onto `User`; data-migration bullet (backfill owner).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#2.3] — architecture conflicts: data model, `create_all`/no-Alembic migration constraint.
- [Source: _bmad-output/implementation-artifacts/10-1-user-model-sessions-auth-gate.md] — `User` model (dormant settings cols), gate, fixture pattern.
- [Source: _bmad-output/implementation-artifacts/10-2-per-user-login-logout.md] — per-user token/OAuth, `_resolve_scheduled_user` bridge, "settings stay on Config until 10.3" deferral.
- [Source: backend/models/user.py + config.py + playlist.py + track_blacklist.py + sync_log.py] — current schema (constraints to reshape).
- [Source: backend/routers/playlists.py + blacklist.py + sync.py + config.py] — query/settings sites to scope.
- [Source: backend/services/spotify.py + sync_engine.py + blacklist_service.py] — dynamic-playlist + settings + blacklist sites to scope.
- [Source: backend/main.py + scheduler.py] — lifespan `create_all`/cron bootstrap (single-job bridge).
- [Source: backend/tests/test_story_9_1.py + test_story_10_2.py] — canonical fixture + engine-patching test patterns.
- [Source: frontend/src/hooks/useConfig.ts + features/config/ConfigForm.tsx + pages/RecentlyAddedPage.tsx + types/index.ts] — `/config` consumers (contract preserved; optional cleanup).
- [Source: CLAUDE.md] — backend conventions, Docker-only tests, Postman sync rule, shadcn CLI / Node 22.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8)

### Debug Log References

- Full suite hang: `test_story_3_4::test_run_sync_preserves_playlist_on_harvest_error` looped forever. Root cause: the 10.3-rewritten test seeded a `User` but left `target_playlist_id=None`, so `run_sync` reached the *real* `get_or_create_dynamic_playlist` (unmocked here), which paginates `current_user_playlists` until `page["next"] is None` — and an unconfigured `MagicMock` never returns `None`. Fixed by seeding `user.target_playlist_id="dyn_id"` so the function short-circuits. Pure test defect, not a prod loop.
- `test_story_3_5` (3 errors) / lifespan boot crash: `sqlite3.OperationalError: no such column: user.last_sync_at`. The migration never added `last_sync_at` to a *pre-existing* `user` table (10.1 created `user` without it; `create_all` never alters). **Genuine prod-upgrade bug** — added `migrations._migrate_user` (`ALTER TABLE user ADD COLUMN last_sync_at`) and run it *before* `_resolve_owner_id` (which issues `SELECT user.*`).
- `test_story_9_8` (3 failures): `no such column: track_blacklist.user_id` + `'NoneType' has no attribute 'id'`. The 10.3 service became user-scoped (`get_blacklisted_ids(session, user.id)` over module-level `Session(engine)`), but the service tests still called `get_playlist_tracks_page(...)` with no `user` and against the real (stale) DB. Fixed per the story's own testing standard: patch `services.spotify.engine` to the in-memory engine and pass a `user`.
- `test_story_8_5::test_run_sync_restores_track_after_blacklist_delete`: `TrackBlacklist` seeded without `user_id` → `NOT NULL` on the new composite PK. Stamped `user_id=_user.id`.

### Completion Notes List

This story's implementation existed in the uncommitted working tree (Epic 10 was developed together, 10.1→10.2→10.3) but was never validated or closed out: all task checkboxes were unchecked, the full suite was red, and the Postman collection was stale. This session verified the implementation against every AC, fixed the defects below, brought the suite to green, and synced Postman.

- **Schema (AC#1–3):** `user_id` FK+index on `Playlist`/`track_blacklist`/`sync_log`; `Playlist` composite-unique `(user_id, spotify_id)`; `track_blacklist` composite PK `(spotify_id, user_id)`; `User.last_sync_at` added. (Models were already edited; verified correct.)
- **Migration (AC#4):** `migrations.run_migrations(engine)` — idempotent `ADD COLUMN`/rebuild + owner backfill + `Config`→`User` settings copy. **Fixed two real gaps:** (1) added `_migrate_user` so a legacy `user` table gains `last_sync_at` (required for any real prod upgrade, not just a fresh DB), ordered before owner resolution; (2) verified the no-owner-with-legacy-blacklist-rows deferral is intentional and idempotent.
- **Scoping (AC#5–8, #12):** confirmed every `select(Playlist/TrackBlacklist/SyncLog)` in app code is `.where(... .user_id == ...)`; `toggle_playlist`, the whole blacklist router, and `get_sync_logs`/`get_sync_status` carry `CurrentUserDep`; dynamic playlist reads/writes `user.target_playlist_id`.
- **Settings + scheduler bridge (AC#9–10):** `/config` GET/PATCH operate on `current_user`; JSON shapes unchanged; `PUT /config` + `ConfigWrite` removed (Open Question #2 default); lifespan + PATCH bootstrap cron from the owner/acting user via `_resolve_scheduled_user()`, tagged `# TODO(10.4)`.
- **Config model removed (AC#11):** grep confirms zero `Config` model imports/usages in app code; `models/config.py` deleted; migration reads the legacy `config` *table* via raw SQL only.
- **Tests (AC#13):** full suite **180 passed, 0 failed** via Docker. Added `test_migration_adds_last_sync_at_to_legacy_user_table` to cover the new `_migrate_user` behavior (the pre-existing migration tests built `user` from the current model and so never exercised the real prod path). Frontend `npm run build` (Node 22 in container) passes.
- **Postman (AC#14):** collection `31411470-…` updated — removed `PUT /config`; added per-user-scoping notes to `/config`, `/playlists`, `/blacklist`, `/sync/logs`, `/recently-added`; verified via follow-up GET.

Open questions for the user (defaults taken, flagged in PR): #1 `Config` model **removed** (table kept as backup); #2 `PUT /config` **removed**; #3 prod data **backfilled** to owner (not reset); #4 multi-user cron defers to 10.4 (only the owner's cron schedules until then). Note: the local dev `/data/app.db` is in a legacy state (12 playlists / 6 blacklist / 14 sync_log rows but **0 logged-in users**) — the migration correctly defers the `track_blacklist` rebuild there until someone logs in; this is the designed prod-safe behavior, and CI/fresh installs are unaffected.

### File List

**New:**
- `backend/migrations.py`
- `backend/tests/test_story_10_3.py`

**Modified (this session):**
- `backend/migrations.py` — added `_migrate_user` (legacy `user.last_sync_at`), reordered before owner resolution
- `backend/tests/test_story_3_4.py` — seed `target_playlist_id` to stop MagicMock pagination hang
- `backend/tests/test_story_8_5.py` — stamp `user_id` on seeded `TrackBlacklist`
- `backend/tests/test_story_9_8.py` — patch `services.spotify.engine` + pass `user` in service/route tests

**Modified (Epic 10 working tree — 10.3 scope, verified):**
- `backend/models/__init__.py`, `backend/models/user.py`, `backend/models/playlist.py`, `backend/models/track_blacklist.py`, `backend/models/sync_log.py`
- `backend/routers/config.py`, `backend/routers/playlists.py`, `backend/routers/blacklist.py`, `backend/routers/sync.py`
- `backend/services/blacklist_service.py`, `backend/services/spotify.py`, `backend/services/sync_engine.py`
- `backend/main.py`
- Existing test repairs: `backend/tests/test_story_3_1.py`, `3_2.py`, `3_3.py`, `5_1.py`, `5_2.py`, `7_1.py`, `8_1.py`, `8_2.py`, `8_3.py`, `9_1.py`, `9_7.py`, `2_4.py`

**Deleted:**
- `backend/models/config.py`

**External:**
- Postman collection `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6` (removed `PUT /config`; per-user scoping notes)

### Change Log

| Date | Change |
|------|--------|
| 2026-06-09 | Story created (context engine analysis — Epic 10 data scoping migration, built from Sprint Change Proposal §4.3/§4.2/§2.3 + Story 10.1 + Story 10.2 + exhaustive codebase analysis). |
| 2026-06-10 | Dev-story: validated existing Epic 10 working-tree implementation against all 14 ACs. Fixed migration gap (`_migrate_user` adds `last_sync_at` to legacy `user` table, ordered before owner resolution) and 3 test defects (3_4 pagination hang, 8_5 missing `user_id`, 9_8 unscoped/real-DB service tests). Added `test_migration_adds_last_sync_at_to_legacy_user_table`. Full suite green (180 passed); frontend build green; Postman synced. Status → review. |
