# Story 10.4: Per-User Scheduler Jobs

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
<!-- Source of truth: Epic 10 was NOT added to epics.md, and prd.md/architecture.md were NOT amended.
     This story is built from the Sprint Change Proposal (authoritative spec for Epic 10) + Story 10.2
     (the _resolve_scheduled_user bridge) + Story 10.3 (which explicitly deferred per-user jobs here)
     + direct codebase analysis of scheduler.py / sync_engine.py / main.py / routers. See References. -->

## Story

As a **Spotify user of the multi-tenant deployed app**,
I want **my automatic sync to run on my own cron schedule, independently of every other user**,
so that **each user's "Recent Adds" playlist refreshes on their own configured cadence — not just the owner's, which is the only schedule that currently runs**.

## Context & Scope Boundary (READ FIRST)

This is the **scheduler multi-tenancy** story of Epic 10, and the last functional gap before prod hardening (10.5). Stories 10.1 → 10.2 → 10.3 made **identity, tokens, and all data/settings** per-user. But the **background scheduler is still single-job**: there is exactly **one** APScheduler job (`id="sync_job"`) that runs as the **owner/first user** via the `_resolve_scheduled_user()` bridge. If a second user logs in and sets a different `cron_expr`, **their schedule never fires** — only the owner's cron is registered. 10.4 closes that gap: **one APScheduler job per user** (`sync_{user_id}`), each driven by that user's own `cron_expr`, each running the sync as that user.

The bridge was always meant to be temporary — every touchpoint is tagged `# TODO(10.4)`. **This story removes the bridge.**

**IN SCOPE (10.4):**
- **`run_sync` becomes user-parameterized:** `run_sync(user_id: int)` instead of `run_sync()` + internal `_resolve_scheduled_user()`. The scheduled job passes the user id as an argument; the manual `POST /sync/run` endpoint passes `current_user.id`.
- **Per-user job registration:** `scheduler.py` gains a function to register/remove **one job per user**, `job_id = f"sync_{user_id}"`, `args=[user_id]`, from that user's `cron_expr` (or remove the job when their cron is `None`). Keep `replace_existing=True`, `max_instances=1`, `coalesce=True` per the existing single-job pattern (AC#5 of Story 4.1 — no concurrent runs **per user**).
- **Startup reconcile:** the `main.py` lifespan registers a per-user job for **every** user with a non-null `cron_expr` (iterate all users), and **removes the legacy global `sync_job`** if it is still present in the persisted `SQLAlchemyJobStore` (prod-upgrade safety — see "The prod-upgrade hazard" below).
- **Live reconfiguration stays per-user:** `PATCH /config` re-bootstraps **only the acting user's** job (`sync_{current_user.id}`) from their new `cron_expr`, instead of re-bootstrapping the single global job.
- **Remove the `_resolve_scheduled_user()` bridge** and every `# TODO(10.4)` tag it left behind (`scheduler.py` is fine, but `sync_engine.run_sync`, `routers/config.py`, `main.py`, and `routers/sync.py POST /run` all carry bridge logic/tags).
- **Tests:** new `test_story_10_4.py` (two users with different crons → two distinct jobs; `run_sync(user_id)` runs as that user; PATCH re-bootstraps only that user's job; startup registers all users + removes legacy `sync_job`). Repair `test_story_4_1.py` (job-id assertion `sync_job` → per-user), `test_story_4_2.py` (PATCH now bootstraps the user's job), and the `run_sync()`-no-arg call sites in `test_story_3_3.py`, `3_4.py`, `8_5.py`.

**EXPLICITLY OUT OF SCOPE — do NOT implement here:**
- **Prod hardening** (redirect-URI registration, Secure/HttpOnly cookie verification in prod, returning-user end-to-end) → **Story 10.5**.
- **User deletion / job cleanup on logout.** Logout (10.2) only clears the session cookie — the `User` row and its data stay in the DB for next login, so its scheduled job should **keep running** (the sync is server-side and needs no active browser session). Do NOT add job teardown on logout. (Only a user explicitly clearing their `cron_expr` via PATCH removes their job.)
- **Re-litigating identity/token/login or data scoping** — done in 10.1/10.2/10.3. Do NOT touch `SQLiteCacheHandler`, `_get_spotify_oauth`, the login round-trip, or the query-scoping from 10.3.
- **Changing the sync pipeline itself** (harvest/dedup/slice/push) — `run_sync`'s body is correct as of 10.3; 10.4 only changes **how the acting user is supplied** (argument, not `_resolve_scheduled_user()`).

**Default design decisions (committed; flagged as Open Questions at the end):**
1. **`run_sync(user_id: int)`** (pass the id, not the `User` object) — the `SQLAlchemyJobStore` pickles job args, and an `int` id is trivially serializable/stable across restarts whereas a `User` ORM instance is not. `run_sync` re-loads the `User` from the DB by id at the top (it already opens its own `Session`).
2. **Startup reconcile removes the legacy `sync_job`** and any `sync_{id}` job whose user no longer has a cron, then (re)adds a job for every user with a cron. This makes startup idempotent and prod-upgrade-safe.

## Acceptance Criteria

1. **One job per user, keyed by user id.** When the scheduler bootstraps a user with a non-null `cron_expr`, it registers an APScheduler job with `id == f"sync_{user_id}"`, triggered by `CronTrigger.from_crontab(user.cron_expr)`, calling `run_sync` with that user's id as its argument. Two users with different `cron_expr` values produce **two distinct jobs** (`sync_1`, `sync_2`) that fire independently on their own schedules.

2. **The scheduled run executes as the correct user.** When `sync_{user_id}` fires, the sync runs entirely against that `user_id`'s data and Spotify account: it reads that user's `playlist_size`/`last_sync_at`/included `Playlist` rows/blacklist, builds a client from that user's token, writes the `SyncLog` row and `last_sync_at` back against that user. User A's scheduled job never touches user B's data. (The pipeline body is unchanged from 10.3 — only the acting user is now the passed `user_id`, not "the first user".)

3. **`run_sync` is user-parameterized; the bridge is gone.** `services/sync_engine.run_sync` takes `user_id: int` and resolves the `User` by that id (returning a skip/no-op dict if the user no longer exists). The `_resolve_scheduled_user()` helper and **every `# TODO(10.4)` tag** that referenced it (`sync_engine.py`, `main.py`, `routers/config.py`) are removed. No code path resolves "the first/owner user" to decide whose sync runs.

4. **Manual sync runs as the requester.** `POST /sync/run` injects `CurrentUserDep` and calls `run_sync(current_user.id)`, so a manual trigger syncs the **logged-in** user (not the owner). Its success/`ValueError`(400)/`Exception`(500) behavior is otherwise unchanged.

5. **Live reconfiguration is per-user.** `PATCH /config` re-bootstraps **only the acting user's** job: changing `current_user.cron_expr` registers/replaces `sync_{current_user.id}` with the new schedule; setting `cron_expr` to `None`/empty removes `sync_{current_user.id}` (and only that job). Another user's job is never added, removed, or rescheduled by one user's PATCH.

6. **Startup registers every scheduled user.** On lifespan startup (after `create_all` + `run_migrations` + `scheduler.start()`), the app iterates all `User` rows and registers a `sync_{id}` job for each user whose `cron_expr` is non-null. A fresh DB with no users registers no jobs and boots cleanly (no error).

7. **Legacy global job is purged on upgrade (prod-safety).** If the persisted `SQLAlchemyJobStore` still contains the pre-10.4 `id="sync_job"` job (from a prior deployment), startup **removes it**, so the owner's sync does not double-run (once as the orphaned `sync_job`, once as their new `sync_{owner_id}`). Startup is idempotent: running it twice yields the same set of jobs.

8. **Job persistence preserved (FR16/NFR9).** Per-user jobs are stored in the same `SQLAlchemyJobStore` (`sqlite:////data/app.db`) and survive container restart — the existing persistence guarantee from Story 4.1 holds per user. `replace_existing=True` keeps re-registration on every boot idempotent; `max_instances=1` + `coalesce=True` prevent concurrent/duplicate runs **of the same user's** job.

9. **No token/secret leakage; conventions preserved.** No new endpoint or response exposes `client_secret`/`client_id`/`token_json`/tokens (NFR5). Business logic stays in `services/`/`scheduler.py` (not routers); all spotipy calls stay behind `services/spotify.py`; snake_case JSON; arrays returned directly. `POST /sync/run`'s response shape is unchanged.

10. **Full suite green; new behavior covered.** New `test_story_10_4.py` proves: two users → two distinct `sync_{id}` jobs with the right triggers; `run_sync(user_id)` runs as that user (and is a no-op for a missing user id); `PATCH /config` re-bootstraps only the acting user's job; startup registers all cron'd users and removes a pre-existing `sync_job`. `test_story_4_1.py` and `test_story_4_2.py` are updated for the per-user job id / per-user bootstrap; the no-arg `run_sync()` calls in `test_story_3_3.py`/`3_4.py`/`8_5.py` are updated to `run_sync(user_id)`. All pre-existing tests pass. Run via Docker only.

11. **Postman unchanged-or-noted.** No new routes are added. `POST /sync/run` is now request-scoped (runs as the caller) — confirm its description in the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`) reflects "syncs the authenticated user" and verify via a follow-up GET. (Per `CLAUDE.md`, update even when only a response/description shape changes.)

## Tasks / Subtasks

- [x] **Task 1: Per-user job registration in `scheduler.py`** (AC: #1, #5, #7, #8)
  - [x] Add `bootstrap_user_job(user_id: int, cron_expr: str | None) -> None`: if `cron_expr` → `scheduler.add_job(run_sync, CronTrigger.from_crontab(cron_expr), id=f"sync_{user_id}", args=[user_id], replace_existing=True, max_instances=1, coalesce=True)`; else → `if scheduler.get_job(f"sync_{user_id}"): scheduler.remove_job(f"sync_{user_id}")`. (Mirror the existing `bootstrap_scheduler` shape exactly — same kwargs — but parameterized by user.)
  - [x] Add `bootstrap_all_jobs() -> None`: open `with Session(engine) as session:`, `select(User)` all rows, call `bootstrap_user_job(u.id, u.cron_expr)` for each. (This both registers cron'd users and removes jobs for users who cleared their cron.)
  - [x] Add `purge_legacy_global_job() -> None` (or fold into `bootstrap_all_jobs`): `if scheduler.get_job("sync_job"): scheduler.remove_job("sync_job")` — removes the pre-10.4 global job from the persisted store on upgrade (AC#7).
  - [x] **Decision:** keep the old `bootstrap_scheduler(cron_expr)` function? **Removed** (Open Question #2 default) — no caller remains; `test_story_4_1.py` rewritten against `bootstrap_user_job`. Grep confirms zero production references.
  - [x] Import `run_sync` from `services.sync_engine` locally inside the functions (keep the existing circular-import-avoidance pattern from the current `bootstrap_scheduler`).

- [x] **Task 2: `run_sync(user_id)` + remove the bridge** (AC: #2, #3)
  - [x] `services/sync_engine.py`: change `def run_sync() -> dict:` → `def run_sync(user_id: int) -> dict:`. Replace the `user = _resolve_scheduled_user(); if user is None: return {...}` block with `with Session(engine) as session: user = session.get(User, user_id)` then `if user is None: return {"status": "skipped", "reason": "user not found"}`. The rest of the body is unchanged (it already scopes everything to `user.id`).
  - [x] **Delete `_resolve_scheduled_user()`** from `sync_engine.py` and its `# TODO(10.4)` docstring/comment. Grep the whole `backend/` tree for `_resolve_scheduled_user` to confirm zero remaining references. (Also fixed a stale docstring reference in `migrations._resolve_owner_id`.)
  - [x] Remove the `# TODO(10.4)` comment block in `run_sync` (lines ~81–82).

- [x] **Task 3: Wire up lifespan + PATCH /config + manual run** (AC: #4, #5, #6, #7)
  - [x] `main.py` lifespan: after `scheduler.start()`, replace the `_resolve_scheduled_user()` import + `bootstrap_scheduler(...)` call with `purge_legacy_global_job()` then `bootstrap_all_jobs()`. Remove the `# TODO(10.4)` comment.
  - [x] `routers/config.py` `patch_config`: replace `bootstrap_scheduler(current_user.cron_expr)` with `bootstrap_user_job(current_user.id, current_user.cron_expr)`. Update the import (`from scheduler import bootstrap_user_job`). Remove the `# TODO(10.4)` comment.
  - [x] `routers/sync.py` `POST /run`: add `current_user: CurrentUserDep`, call `sync_engine.run_sync(current_user.id)`. Keep the `ValueError`→400 / `Exception`→500 mapping.

- [x] **Task 4: Tests** (AC: #10)
  - [x] New `backend/tests/test_story_10_4.py`: per-user jobs (a), clear-cron-removes-only-that-job (b), `run_sync(user_id)` runs as that user + missing-user no-op (c), `bootstrap_all_jobs` registers cron'd / removes cron-less + empty-db (d), `purge_legacy_global_job` present/absent (e), PATCH /config bootstraps + clears the acting user's job (f).
  - [x] **Repair `test_story_4_1.py`:** rewritten against `bootstrap_user_job` (`id == "sync_1"`, `args=[1]`); trigger-type + idempotency assertions preserved.
  - [x] **Repair `test_story_4_2.py`:** PATCH tests patch `routers.config.bootstrap_user_job` and assert `(user_id, cron_expr)`.
  - [x] **Repair `run_sync()` call sites:** `test_story_3_3.py`, `test_story_3_4.py`, `test_story_8_5.py` now call `run_sync(1)` (the seeded user's id).
  - [x] Run the FULL suite: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **192 passed**.

- [x] **Task 5: Postman + docs** (AC: #11)
  - [x] Updated the collection (UID `31411470-dcbaa843-f4f8-42d7-a51d-ab52e0ae35e6`): `POST Run Sync` description now states it runs the **authenticated user's** sync (was implicitly the owner). No new routes. Verified via follow-up GET (200).

## Dev Notes

### Authoritative spec & how 10.4 fits
- **Source of truth = the Sprint Change Proposal** (Epic 10 was never written into `epics.md`; PRD/architecture were not amended).
- §2.3 (architecture conflicts): *"**Scheduler** — One global cron job → **per-user jobs** (`job_id = f"sync_{user_id}"`) from each user's `cron_expr`."*
- §4.2: *"**Scheduler**: one APScheduler job per user (`sync_{user_id}`) from that user's `cron_expr`."*
- §4.3 line: *"10.4 — Per-user scheduler jobs (one APScheduler job per user from their `cron_expr`)."*
- **10.3 explicitly deferred this.** Story 10.3 §"Scheduler stays single-job until 10.4": *"The APScheduler job is still one global `sync_job`. 10.3 does NOT create per-user jobs. It only changes the source of the cron from `Config.cron_expr` to the owner user's `cron_expr` (via `_resolve_scheduled_user()`)… When multiple users have different `cron_expr` values, only the owner's wins — that incorrectness is explicitly 10.4's job. Tag every bridge touchpoint `# TODO(10.4)`."* → **10.4 removes the bridge and creates per-user jobs.**
- 10.3 Open Question #4 surfaced exactly this gap to the user: *"with the single-job bridge, only the owner's `cron_expr` schedules. If a second user logs in and sets a different cron before 10.4 lands, their schedule won't run."* — **10.4 resolves it.**

### What 10.1/10.2/10.3 already built (do NOT redo)
- **10.1:** `User` model (with `cron_expr`, `playlist_size`, `target_playlist_id`), session middleware, `get_current_user`/`CurrentUserDep`, the 401 gate on the 5 business routers.
- **10.2:** per-user token (`SQLiteCacheHandler(user_id)`), per-user OAuth (`_get_spotify_oauth(user)`, `get_authenticated_client(user)`), login round-trip, and **the `_resolve_scheduled_user()` bridge** introduced so the background job (which has no request session) could run as *a* user. **10.4 deletes this bridge.**
- **10.3:** `user_id` on `Playlist`/`track_blacklist`/`sync_log`, `User.last_sync_at`, every query scoped to `current_user`, settings moved off `Config` onto `User`, and the scheduler **sourced** from the owner user's `cron_expr` (single job, still). The `run_sync` body is already fully user-scoped against the resolved `user` — 10.4 just changes how that user is chosen.

### The current single-job bridge (exactly what to replace)
- `scheduler.py`: `bootstrap_scheduler(cron_expr)` adds/removes **one** job `id="sync_job"` calling `run_sync` (no args), `replace_existing=True`, `max_instances=1`, `coalesce=True`.
- `services/sync_engine.py`: `run_sync()` calls `_resolve_scheduled_user()` (→ `session.exec(select(User)).first()`), returns `{"status":"skipped","reason":"no authenticated user"}` if None, else runs the full pipeline against that user.
- `main.py` lifespan: `user = _resolve_scheduled_user(); bootstrap_scheduler(user.cron_expr if user else None)` under a `# TODO(10.4)`.
- `routers/config.py` PATCH: `bootstrap_scheduler(current_user.cron_expr)` under a `# TODO(10.4)`.
- `routers/sync.py` `POST /run`: `sync_engine.run_sync()` — **no `current_user`** today (it relies on the bridge resolving the first user). 10.4 gives it `CurrentUserDep`.

### APScheduler + SQLAlchemyJobStore specifics (get persistence right)
- The job store is `SQLAlchemyJobStore(url="sqlite:////data/app.db")` (in `scheduler.py`) — the same DB file as the app (AR3, FR16). Jobs are **pickled**, including the callable reference (`services.sync_engine:run_sync`) and `args`.
- **Pass `args=[user_id]` (a plain `int`)** — NOT a `User` ORM object (un-pickleable / stale across restarts). `run_sync` re-loads the row by id inside its own `Session`.
- `id=f"sync_{user_id}"` makes each job addressable for `replace_existing`/`remove_job`. `replace_existing=True` → re-bootstrapping on every boot is idempotent (AC#8).
- **The prod-upgrade hazard (AC#7):** the deployed prod DB already contains a persisted `sync_job` row (from 4.1/10.3). On the 10.4 deploy, the store restores `sync_job` (→ runs `run_sync` with NO args → `TypeError`, or, if you kept a default, runs as the owner) **and** the new `sync_{owner_id}` runs too → double sync + a crash. So startup MUST `remove_job("sync_job")` before/while registering per-user jobs. Mirror the care 10.3 took with its legacy-table migration. This is a real prod-data path, not just a test concern — verify the removal is unconditional-but-guarded (`if scheduler.get_job("sync_job")`).
- `scheduler.start()` is called **before** bootstrap in the lifespan; `add_job`/`remove_job` after start is supported and is the existing pattern.

### Concurrency / correctness notes
- `max_instances=1` + `coalesce=True` are **per job id**, so they correctly prevent a single user's sync from overlapping itself — they do NOT (and should not) serialize *different* users' syncs. Two users' jobs firing at the same minute run concurrently; that's fine — each has its own data, token, and dynamic playlist (10.3).
- `run_sync` opens its own `Session(engine)` and does blocking spotipy I/O. It runs on APScheduler's thread pool (`BackgroundScheduler`), not the event loop — unchanged from today. No async concerns.
- The manual SSE path (`GET /sync/stream` → `_run_sync_stream(current_user)`) is **already** per-user (10.3) and does NOT go through `run_sync` — leave it alone. Only `POST /sync/run` (the non-streaming manual trigger) calls `run_sync`.

### Testing standards (match the repo)
- Tests ONLY via Docker: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v`.
- **Scheduler unit tests** mock the scheduler methods directly: `patch("scheduler.scheduler.add_job")`, `patch("scheduler.scheduler.get_job", ...)`, `patch("scheduler.scheduler.remove_job")` (canonical: `test_story_4_1.py`). Assert on `call_args.kwargs["id"]`/`["args"]` and the `CronTrigger` instance in `call_args.args[1]`.
- **PATCH tests** patch the symbol *as imported into the router*: `patch("routers.config.bootstrap_user_job")` (canonical: `test_story_4_2.py` patches `routers.config.bootstrap_scheduler`).
- **`run_sync(user_id)` integration tests** seed a `User` (+ included `Playlist` rows, all `user_id`-stamped per 10.3) in the in-memory engine, mock the spotify service boundary (`patch("services.sync_engine.spotify_service.<fn>", ...)` and `services.spotify` internals), and assert the `SyncLog`/`last_sync_at` are written against the passed id. Reuse the seeding pattern already in `test_story_3_4.py`/`8_5.py` (post-10.3 they seed a `User`; just pass `user.id` to `run_sync`).
- The `test_story_3_4.py` pagination-hang lesson (from 10.3): always seed `user.target_playlist_id` so the unmocked `get_or_create_dynamic_playlist` short-circuits and doesn't loop on a `MagicMock`.
- Fixture pattern (canonical: `test_story_9_1.py` / `test_story_4_2.py`): in-memory SQLite + `StaticPool`, `create_all`, `session` fixture, `client` fixture overriding `get_session` + `get_current_user`. Clear `app.dependency_overrides` on teardown.

### Anti-patterns to avoid
- ❌ Do NOT pass a `User` object as a job `arg` — pass the `int` id (job store pickles args; ids must be stable/serializable).
- ❌ Do NOT leave the legacy `sync_job` in the persisted store — purge it on startup, or prod double-runs / crashes on the no-arg call.
- ❌ Do NOT keep `_resolve_scheduled_user()` "just in case" — it is the bridge; deleting it is the point. Grep to prove zero references remain.
- ❌ Do NOT make `max_instances`/`coalesce` serialize across users — they're per-job-id and must stay that way.
- ❌ Do NOT touch `_run_sync_stream`/`GET /sync/stream` — already per-user, does not use `run_sync`.
- ❌ Do NOT add job teardown on logout — server-side syncs must continue for logged-out-but-registered users (logout only clears the cookie; data + schedule persist).
- ❌ Do NOT re-introduce any "owner/first user" resolution into the run path.
- ❌ Do NOT forget to give `POST /sync/run` a `CurrentUserDep` — without it, after removing the bridge, `run_sync()` has no user id to pass.

### Project Structure Notes
- **New:** `backend/tests/test_story_10_4.py`.
- **Edits:** `backend/scheduler.py` (per-user `bootstrap_user_job` + `bootstrap_all_jobs` + `purge_legacy_global_job`; remove/retire `bootstrap_scheduler`), `backend/services/sync_engine.py` (`run_sync(user_id)`; delete `_resolve_scheduled_user`), `backend/main.py` (lifespan reconcile), `backend/routers/config.py` (PATCH → `bootstrap_user_job`), `backend/routers/sync.py` (`POST /run` gains `CurrentUserDep`, passes `current_user.id`).
- **Test repairs:** `backend/tests/test_story_4_1.py`, `test_story_4_2.py`, `test_story_3_3.py`, `test_story_3_4.py`, `test_story_8_5.py`.
- **Conventions (CLAUDE.md):** business logic in `services/`/`scheduler.py` not routers; spotipy only via `services/spotify.py`; snake_case JSON; no response wrapper; tests Docker-only; Postman synced on any API contract/description change.

### Open questions for the user (do not block implementation; flag in PR)
1. **Job lifecycle for inactive users.** A user who logged in once, set a cron, then never returns still has a `sync_{id}` job firing forever (running their stored token). Default: **keep it running** (the product promise is "stays current automatically"). If unbounded background jobs for dormant accounts are a concern, a future story could prune jobs after N consecutive token-refresh failures — out of scope here.
2. **Remove `bootstrap_scheduler` entirely?** Default = **remove** (no caller remains; `test_story_4_1` rewritten to `bootstrap_user_job`). Alternative: keep it as a thin wrapper, but it would be dead code.
3. **Startup reconcile strategy.** Default = iterate `User` rows + `bootstrap_user_job` each + purge `sync_job`. Alternative (more aggressive): enumerate all `scheduler.get_jobs()`, drop any `sync_*` not backed by a current cron'd user. Default is sufficient because `bootstrap_user_job(id, None)` already removes a cron-less user's job; the extra sweep only matters if a `User` row were hard-deleted (no delete path exists yet).

### References
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.3] — Epic 10 story breakdown (10.4 = per-user scheduler jobs).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#4.2] — "one APScheduler job per user (`sync_{user_id}`) from that user's `cron_expr`".
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-09-multi-user-oauth.md#2.3] — scheduler conflict: global job → per-user jobs.
- [Source: _bmad-output/implementation-artifacts/10-3-data-scoping-migration.md#Scheduler-stays-single-job-until-10.4] — the bridge 10.4 removes; Open Question #4 (the gap this story closes).
- [Source: _bmad-output/implementation-artifacts/10-2-per-user-login-logout.md] — origin of `_resolve_scheduled_user()` bridge; per-user token/OAuth used by `run_sync`.
- [Source: backend/scheduler.py] — current single `sync_job` `bootstrap_scheduler`; `SQLAlchemyJobStore` config.
- [Source: backend/services/sync_engine.py:13-22,71-154] — `_resolve_scheduled_user()` + `run_sync()` body (already user-scoped to the resolved user).
- [Source: backend/main.py:21-34] — lifespan: `create_all` → `run_migrations` → `scheduler.start()` → bridge bootstrap (`# TODO(10.4)`).
- [Source: backend/routers/config.py:46-68] — PATCH re-bootstrap (`# TODO(10.4)`).
- [Source: backend/routers/sync.py:35-42] — `POST /sync/run` → `run_sync()` (no current_user yet).
- [Source: backend/tests/test_story_4_1.py + test_story_4_2.py] — canonical scheduler/PATCH test patterns to adapt.
- [Source: backend/tests/test_story_3_4.py + test_story_8_5.py + test_story_3_3.py] — `run_sync()` call sites to update; user-seeding + spotify-mock pattern.
- [Source: _bmad-output/implementation-artifacts/4-1-scheduler-bootstrap-job-persistence.md] — job-persistence intent (FR16/NFR9), `max_instances=1`/`coalesce=True` rationale.
- [Source: CLAUDE.md] — backend conventions, Docker-only tests, Postman sync rule.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8)

### Debug Log References

- Full suite run: `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → **192 passed, 28 warnings** (warnings are pre-existing `datetime.utcnow()` deprecations, not introduced by this story).
- `grep -rn "_resolve_scheduled_user\|bootstrap_scheduler" backend/**/*.py` → zero production references; remaining hits are the rewritten tests (`test_story_4_1.py`/`4_2.py`).

### Completion Notes List

- **Per-user jobs (AC#1,#5,#8):** `scheduler.bootstrap_user_job(user_id, cron_expr)` registers `sync_{user_id}` with `args=[user_id]`, `replace_existing/max_instances=1/coalesce=True` (mirrors the old single-job kwargs); a `None` cron removes only that user's job. Job store/persistence unchanged.
- **Bridge removed (AC#3):** `_resolve_scheduled_user()` deleted; `run_sync(user_id)` re-loads the `User` by id in its own `Session` and returns `{"status":"skipped","reason":"user not found"}` for a missing id. The pipeline body is otherwise unchanged from 10.3.
- **Startup reconcile (AC#6,#7):** lifespan now calls `purge_legacy_global_job()` (drops a persisted pre-10.4 `sync_job` on upgrade) then `bootstrap_all_jobs()` (one job per cron'd user; removes jobs of users who cleared their cron). Idempotent via `replace_existing`.
- **Manual run (AC#4):** `POST /sync/run` gained `CurrentUserDep` and calls `run_sync(current_user.id)`; SSE `GET /sync/stream` left untouched (already per-user, does not use `run_sync`).
- **Live reconfig (AC#5):** `PATCH /config` re-bootstraps only `sync_{current_user.id}`.
- **Open Question #2 resolved:** `bootstrap_scheduler` removed entirely (would be dead code).
- **Open Questions #1 (dormant-user jobs keep running) and #3 (reconcile strategy)** kept at their defaults; flagged for PR per Dev Notes.
- **Postman (AC#11):** `POST Run Sync` description updated to "authenticated user's sync"; verified via GET.

### File List

- `backend/scheduler.py` (modified — `bootstrap_user_job` / `bootstrap_all_jobs` / `purge_legacy_global_job`; removed `bootstrap_scheduler`)
- `backend/services/sync_engine.py` (modified — `run_sync(user_id)`; deleted `_resolve_scheduled_user`)
- `backend/main.py` (modified — lifespan reconcile)
- `backend/routers/config.py` (modified — PATCH → `bootstrap_user_job`)
- `backend/routers/sync.py` (modified — `POST /run` gains `CurrentUserDep`)
- `backend/migrations.py` (modified — stale docstring reference to deleted helper)
- `backend/tests/test_story_10_4.py` (new)
- `backend/tests/test_story_4_1.py` (modified — rewritten for `bootstrap_user_job`)
- `backend/tests/test_story_4_2.py` (modified — patch `bootstrap_user_job`)
- `backend/tests/test_story_3_3.py` (modified — `run_sync(1)`)
- `backend/tests/test_story_3_4.py` (modified — `run_sync(1)`)
- `backend/tests/test_story_8_5.py` (modified — `run_sync(1)`)

### Change Log

| Date | Change |
|------|--------|
| 2026-06-10 | Story created (context engine analysis — Epic 10 per-user scheduler jobs, built from Sprint Change Proposal §4.3/§4.2/§2.3 + Story 10.2 bridge + Story 10.3 deferral/Open-Question #4 + exhaustive codebase analysis of scheduler.py/sync_engine.py/main.py/routers). |
| 2026-06-10 | Implemented per-user scheduler jobs: `sync_{user_id}` jobs from each user's `cron_expr`, `run_sync(user_id)`, startup reconcile + legacy `sync_job` purge, per-user PATCH re-bootstrap, request-scoped `POST /sync/run`. Removed `_resolve_scheduled_user()` bridge + `bootstrap_scheduler`. New `test_story_10_4.py`; repaired tests 4_1/4_2/3_3/3_4/8_5. Full suite 192 passed. Postman `POST Run Sync` description updated. |
