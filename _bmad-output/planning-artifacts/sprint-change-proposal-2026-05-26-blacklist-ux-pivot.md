# Sprint Change Proposal — Blacklist UX Pivot

**Date:** 2026-05-26
**Author:** Kevin (with Amelia, dev agent)
**Scope classification:** Moderate (backlog reorg + one new story; touches backend + shared frontend component)
**Trigger:** Manual smoke of `/playlists/liked_songs` after Story 9.6 ship revealed two gaps with the current blacklist UX.

---

## 1. Issue Summary

After implementing Epic 8 (Recently Added + blacklist) and Epic 9 (Playlist Detail), the dogfooding revealed that the current blacklist UX is **destructive and opaque**:

1. **Blacklisted tracks vanish from lists immediately** (optimistic remove in `useBlacklistTrack`). The user has **no way to see what they've already hidden**, no way to unhide accidental clicks, and no recourse if they want to review the hidden set.
2. **No filter to focus on "hidden only" tracks** — even if there were a viewer, the user wants to be able to scope the existing playlist view to just the hidden ones (e.g. to review or restore in bulk).

The current implementation treats blacklist as **soft-delete with no inverse**. The user wants **soft-flag with visual feedback and a focused review mode**.

**Evidence:**
- `frontend/src/hooks/useBlacklist.ts` lines 24-42: optimistic mutation removes the track from `['recently-added']` and `['playlist-tracks', *]` caches.
- `backend/routers/blacklist.py`: `DELETE /blacklist/{id}` already exists but no UI surfaces it.
- `frontend/src/components/TrackRow.tsx` lines 144-150: only one dropdown action ("Hide from Recent Adds"); no "Unhide" path.

---

## 2. Impact Analysis

### Epic Impact

- **Epic 8 (Recently Added & Blacklist)** — UX pivot required (gray-out instead of remove). Backend response shape gains one field. No NFR regression.
- **Epic 9 (Playlist Detail)** — same UX pivot for the per-track action; new "Hidden only" filter toggle added to the hero actions row (alongside the Story 9.5 search input).

### Story Impact

| Story | Status | Impact |
|-------|--------|--------|
| 8.4 — Per-Track Blacklist Action | review | **Amend** AC #2 (optimistic remove → optimistic gray-out). |
| 8.6 — Recently Added Perf & Polish | review | **No code change** — perf ACs still valid. Note the cache-mutation pattern changed from filter to flag. |
| 9.4 — Per-Track Actions on Playlist Detail | review | **Amend** the "optimistic UI" note (remove row → flag row). |
| 9.5 — Filter Tracks within Playlist | review | **No change.** Search input stays; new "Hidden only" toggle is a separate AC in the new story. |
| 9.6 — Virtualization | review | **No change.** Virtualized branch is agnostic to row visual state — the `isBlacklisted` flag is rendered by `TrackRow`. Threshold logic untouched. |
| **NEW: 9.7 — Blacklist UX: gray-out + hidden-only filter** | backlog | **Add** new story (see §4). |

### Artifact Conflicts

- **PRD** — FR33 ("Per-track 'Hide from Recent Adds' action that adds the track to a blacklist") stays valid in spirit; add a note about visual semantics and an inverse "Unhide" action. New FR for "Hidden only" filter toggle.
- **Architecture** — none. No new module, no schema change (blacklist table already exists). One new bool field on track DTOs is additive.
- **UX Design** — `ux-design/README.md` "TrackRow > Column 6 (overflow)" section needs the additional "Unhide" menu item state and the grayed-row visual treatment. Playlist hero actions row gets the new toggle button.
- **Postman collection** — `/recently-added` and `/playlists/{id}/tracks` response shapes gain `is_blacklisted` field — update example responses per [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md).

### Technical Impact

- **Backend** (small, additive):
  - `RecentlyAddedTrack` Pydantic model gains `is_blacklisted: bool`.
  - `services/spotify.get_recently_added_tracks()` and `services/spotify.get_playlist_tracks()` query the blacklist table once per call and set the flag on each returned track. Trivial set-membership join (SELECT all `spotify_id` from `track_blacklist`, build a `set[str]`, check per track).
- **Frontend** (medium):
  - `RecentlyAddedTrack` type and `Track` adapter gain `isBlacklisted: boolean`.
  - `TrackRow` renders dimmed visual when `track.isBlacklisted` (`opacity-50` + muted text). The play icon hover-state can be replaced by a `Lock` or kept as-is.
  - Dropdown menu shows **"Hide from Recent Adds"** OR **"Unhide"** based on `track.isBlacklisted`.
  - `useBlacklistTrack` optimistic mutation changes: **set `is_blacklisted: true`** on the matching track in `['recently-added']` and `['playlist-tracks', *]` caches (instead of filtering out).
  - New hook `useUnblacklistTrack` wrapping `DELETE /blacklist/{id}` with the inverse optimistic mutation.
  - `PlaylistDetailPage`: add toggle button "Hidden only" (icon: `EyeOff` filled when active) in the hero actions row, next to the search input. Composes with Story 9.5 filter.

### Risk Assessment

- **Low risk overall.** The blacklist table schema is unchanged. The new `is_blacklisted` field on the API response is additive and backwards-compatible. Story 9.6 virtualization works on `tracks.length`, which is unchanged. Test suite stability expected (existing 127 backend tests untouched; 4 new tests for the join logic).
- **Edge case:** if a user blacklists a track in a SOURCE playlist, the track remains visible+grayed in both `/playlists/{id}/tracks` (still in the playlist) AND on `/recently-added` for the window between the blacklist click and the next sync (after which it's pushed out of the dynamic playlist — invisible again, but for the right reason). This matches the user's mental model.

### Timeline Impact

One new story (~half a day of dev). No epic delay. Recommend implementing **before closing Epic 8/9 retrospectives** so the UX is consistent for the whole blacklist feature surface.

---

## 3. Recommended Approach

**Direct Adjustment:** add **Story 9.7** to Epic 9 (since the new "Hidden only" toggle lives on the Playlist Detail page, it's a natural fit). Amend Stories 8.4 and 9.4 to reflect the new optimistic-flag semantics (text-only updates to their `Dev Notes` / `Completion Notes`, no code change needed — the code change is fully delivered by 9.7).

**No rollback** of Stories 8.4 / 9.4 / 9.6 needed. They land as-is; 9.7 replaces the destructive mutation with a flag mutation in `useBlacklistTrack`.

---

## 4. Detailed Change Proposals

### 4.1 New Story 9.7 — Blacklist UX: gray-out + hidden-only filter

```
Story 9.7: Blacklist UX — Visible Gray-Out + Hidden-Only Filter

As a user,
I want blacklisted tracks to remain visible (grayed out) in track lists with an "Unhide" inverse action, AND
a "Hidden only" filter toggle on the Playlist Detail page to focus on what I've hidden,
so that the blacklist becomes a reviewable soft-flag instead of an opaque destructive delete.

Acceptance Criteria:

1. **Backend — track DTOs include `is_blacklisted`.** `RecentlyAddedTrack` (in `backend/routers/recently_added.py` and any shared track model) gains `is_blacklisted: bool`. `services/spotify.get_recently_added_tracks()` and `services/spotify.get_playlist_tracks()` perform a single `select(TrackBlacklist.spotify_id)` per call, build a `set[str]`, and set `is_blacklisted` per returned track. Tests cover the join.

2. **Frontend — `Track` type extended.** `frontend/src/types.ts` `RecentlyAddedTrack` and the `Track` adapter in `TrackListTable.tsx` gain `isBlacklisted: boolean` (snake_case in API per CLAUDE.md, camelCase in adapted UI Track).

3. **TrackRow visual treatment.** When `track.isBlacklisted`, the row renders with `opacity-50` and `text-[var(--text-muted)]` on the title/artist/album/date columns; the cover art and play button stay readable (slightly dimmed). Hover state still works. The row is NOT removed from DOM.

4. **Dropdown menu toggles.** In `TrackRow.tsx`, the first dropdown item is:
   - "Hide from Recent Adds" (icon `EyeOff`) when `!track.isBlacklisted` → fires `onHide(id)`.
   - "Unhide" (icon `Eye`) when `track.isBlacklisted` → fires `onUnhide(id)`.
   `TrackRow` accepts a new optional `onUnhide?: (id: string) => void` prop.

5. **`useBlacklistTrack` — optimistic flag.** Instead of filtering the track out of `['recently-added']` and `['playlist-tracks', *]` caches, mutate it in place: `data.map(t => t.spotify_id === id ? { ...t, is_blacklisted: true } : t)`. Rollback on error restores the previous flag.

6. **New `useUnblacklistTrack` hook.** Wraps `DELETE /blacklist/{spotify_id}` with the inverse optimistic mutation (`is_blacklisted: true → false`).

7. **"Hidden only" toggle on Playlist Detail.** A new button in `PlaylistDetailPage`'s hero actions row (alongside the Story 9.5 search input). Active state visualized with the accent color and `EyeOff` filled icon. When active, the displayed list is `filtered.filter(t => t.is_blacklisted)`. Composes with the existing search filter (logical AND).

8. **Cross-page consistency.** `RecentlyAddedPage` also benefits from gray-out (same `TrackRow`). The "Hidden only" toggle is **NOT** added to Recently Added in this story (out of scope; can be revisited if the user requests).

9. **Sync behavior unchanged.** Story 8.5's sync filter still excludes blacklisted tracks from the dynamic playlist on push. After the next sync, blacklisted tracks naturally fall out of `/recently-added` results (because they're no longer in the Spotify playlist). The gray-out is a UI affordance for the window between blacklist click and next sync, AND for blacklisted tracks that still exist in source playlists.

10. **Tests.**
    - Backend: ≥3 new tests in `tests/test_story_9_7.py` covering: (a) `is_blacklisted=true` set when track is in `track_blacklist`, (b) `is_blacklisted=false` when not, (c) join works for both `/recently-added` and `/playlists/{id}/tracks`. Total backend baseline ≥130.
    - Frontend: type-check via `npm run build` (no TS errors).

11. **Postman.** Update collection examples for `GET /recently-added` and `GET /playlists/{id}/tracks` to include `is_blacklisted` per [`feedback_postman_sync`](../../../home/kevinaubel/.claude/projects/-home-kevinaubel-PERSO-playlist-spotify/memory/feedback_postman_sync.md).

12. **Build & test gates.** `docker exec playlist_spotify-frontend-1 npm run build` → 0 TS errors; `docker exec playlist_spotify-backend-1 /app/.venv/bin/pytest tests/ -v` → ≥130 passed.
```

### 4.2 Amend Story 8.4 — Per-Track Blacklist Action

```
Section: Acceptance Criteria → "Given I click the blacklist action…"

OLD:
**Then** the frontend calls `POST /api/v1/blacklist` with `{"spotify_id": "<id>"}`
and optimistically removes the row from the table.

NEW:
**Then** the frontend calls `POST /api/v1/blacklist` with `{"spotify_id": "<id>"}`
and optimistically marks the row as `is_blacklisted: true` (visually grayed out, NOT removed).
Toggle behavior and "Unhide" action are delivered by Story 9.7.

Rationale: UX pivot — blacklist is a reviewable soft-flag, not a destructive delete.
The track stays in the list with reduced opacity so the user can review or restore it.
```

### 4.3 Amend Story 9.4 — Per-Track Actions on Playlist Detail

```
Section: Implementation hints / Optimistic UI

OLD:
- Optimistic UI: remove row from local table state, restore on error (same pattern as Story 8.4).

NEW:
- Optimistic UI: mark row as `is_blacklisted: true` (gray-out visual), restore flag on error.
  The "Unhide" inverse action and grayed-row treatment are delivered by Story 9.7.

Rationale: aligns with the Story 9.7 pivot. Story 9.4's "Hide" action stays;
the visual semantics change from "remove" to "gray-out + persist in list".
```

### 4.4 PRD — FR amendments

Add a clarifying note to FR33 and a new FR (FR36 or similar) for the "Hidden only" toggle.

```
FR33 — amend tail clause:
OLD: "…adds the track to a persistent blacklist."
NEW: "…adds the track to a persistent blacklist. Blacklisted tracks remain visible
     in track lists with a dimmed/grayed visual treatment and a reversible 'Unhide' action."

FRxx (new): "On the Playlist Detail page, the user can toggle a 'Hidden only' filter
     to display only blacklisted tracks. The filter composes with the search filter (FR47)."
```

### 4.5 UX Design — README update

`_bmad-output/planning-artifacts/ux-design/README.md` section "TrackRow > Column 6 (overflow)":
- Add the "Unhide" menu item state (icon `Eye`, shown when `track.isBlacklisted`).
- Add the grayed-row visual spec: `opacity: 0.5` on the title/artist/album/date columns; cover art opacity unchanged; hover state retained.
- New "Playlist Detail hero actions" sub-section: describe the "Hidden only" toggle button (icon `EyeOff`, active state uses `var(--accent-color)`).

---

## 5. Implementation Handoff

**Scope:** Moderate.

**Route to:** Developer agent (Amelia) for direct implementation of Story 9.7 once the proposal is approved.

**Sequence:**

1. Approve this proposal.
2. Apply amendments §4.2 and §4.3 to Stories 8.4 and 9.4 (text-only updates).
3. Apply amendments §4.4 and §4.5 to PRD and UX README.
4. Add Story 9.7 to `epics.md` Epic 9 section.
5. Run `/bmad-create-story` to generate the comprehensive Story 9.7 file with full context.
6. Run `/bmad-dev-story` to implement Story 9.7.
7. Update Postman collection (§4.1 AC #11).

**Success Criteria:**
- Blacklisting a track grays it out instead of removing it (verified in browser at `/recently-added` and `/playlists/liked_songs`).
- Clicking "Unhide" on a grayed track restores its normal visual state.
- "Hidden only" toggle on Playlist Detail filters to just blacklisted tracks.
- Composition with the Story 9.5 search filter works (search AND hidden-only).
- Backend test suite ≥130; frontend builds clean.
- Postman collection reflects the new `is_blacklisted` field.

**Deliverables:**
- This Sprint Change Proposal (filed at `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-26-blacklist-ux-pivot.md`).
- Story 9.7 file (TBD after `/bmad-create-story`).
- Updated `epics.md`, `prd.md`, `ux-design/README.md`.
- Updated Story 8.4 and 9.4 text (amend-in-place).
