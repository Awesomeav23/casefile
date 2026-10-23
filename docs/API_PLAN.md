# Casefile: API Plan

**Status:** Planning draft. No endpoints exist yet.
**Related:** [ARCHITECTURE](ARCHITECTURE.md) · [DATA_MODEL](DATA_MODEL.md) · [SCREEN_DESIGN](SCREEN_DESIGN.md)

- Base path: `/api/v1/`. JSON only. Timestamps are ISO 8601 UTC. In-world times are `"YYYY-MM-DDTHH:MM"` without a timezone.
- Auth: Django session cookie. Unsafe methods require the `X-CSRFToken` header (ARCHITECTURE §5).
- Errors use the envelope in ARCHITECTURE §6. Codes are listed in §9.
- Content items are addressed by **key** within a playthrough's case. Playthroughs, notes, and theories use UUIDs.
- The OpenAPI schema is generated at `/api/v1/schema/` (drf-spectacular), with interactive docs in development only.

Permission legend: **Public** · **Player** (account holder *or* guest; D-01; a guest identity is created lazily on the first write) · **Account** (logged-in account holder) · **Owner** (the requesting player owns the playthrough; anyone else gets 404) · **Staff**.

---

## 1. Endpoint summary

| Method | Path | Perm | Purpose |
|---|---|---|---|
| GET | `/auth/csrf/` | Public | Set CSRF cookie |
| POST | `/auth/register/` | Public | Create account, log in |
| POST | `/auth/login/` | Public | Log in |
| POST | `/auth/logout/` | Account | Log out |
| GET | `/auth/me/` | Public | Current user, guest status, or neither |
| POST | `/auth/password-reset/` | Public | Request reset email |
| POST | `/auth/password-reset/confirm/` | Public | Set new password with token |
| PATCH | `/me/profile/` | Account | Update display name & preferences |
| POST | `/me/password/` | Account | Change password (`current_password`, `new_password`) |
| GET | `/me/export/` | Account | Download own data (JSON) |
| DELETE | `/me/` | Account | Delete account (requires password) |
| DELETE | `/me/guest/` | Player (guest) | "Forget my progress on this browser": deletes the guest's playthroughs and clears the guest ID |
| GET | `/cases/` | Public | Case library (+ player status for users and guests) |
| GET | `/cases/{slug}/` | Public | Case briefing |
| POST | `/cases/{slug}/playthroughs/` | Player | Start a new playthrough, or return the in-progress one |
| GET | `/playthroughs/` | Player | List own playthroughs |
| GET | `/playthroughs/{id}/` | Owner | Playthrough summary |
| GET | `/playthroughs/{id}/casefile/` | Owner | Everything discovered so far |
| POST | `/playthroughs/{id}/actions/` | Owner | Perform an investigation action |
| GET / POST | `/playthroughs/{id}/flags/` | Owner | List / submit contradiction flags (verified on submit) |
| PATCH / DELETE | `/playthroughs/{id}/flags/{flagId}/` | Owner | Revise (re-verify) / remove an **unconfirmed** flag |
| GET / POST | `/playthroughs/{id}/hints/` | Owner | Offered tracks + revealed tiers / reveal the next tier |
| POST | `/playthroughs/{id}/seen/` | Owner | Mark items as seen (clears "new" badges) |
| POST | `/playthroughs/{id}/heartbeat/` | Owner | Accumulate active play time |
| POST | `/playthroughs/{id}/abandon/` | Owner | Abandon (enables a fresh start) |
| GET / PUT | `/playthroughs/{id}/board/` | Owner | Read / replace evidence board layout |
| GET / POST | `/playthroughs/{id}/notes/` | Owner | List / create notes |
| PATCH / DELETE | `/playthroughs/{id}/notes/{noteId}/` | Owner | Edit / delete note |
| GET / POST | `/playthroughs/{id}/theories/` | Owner | List / create theories |
| PATCH / DELETE | `/playthroughs/{id}/theories/{theoryId}/` | Owner | Edit / delete theory |
| PUT | `/playthroughs/{id}/markers/{personKey}/` | Owner | Set suspicion marker |
| GET | `/playthroughs/{id}/accusation-form/` | Owner | Accusation questions & options |
| POST | `/playthroughs/{id}/accusation/` | Owner | Submit final accusation |
| GET | `/playthroughs/{id}/results/` | Owner | Results & solution (only after accusation) |
| GET | `/me/progress/` | Player | Progress overview & statistics (guests: this browser only) |
| GET | `/staff/cases/` | Staff | All cases incl. drafts |
| POST | `/staff/cases/{slug}/preview/` | Staff | Start a preview playthrough of a draft |
| POST | `/staff/playthroughs/{id}/reveal-all/` | Staff | Discover everything (preview playthroughs only) |

Import and validation are **CLI only** (`manage.py validate_case`, `import_case`). There are no HTTP endpoints for them.

## 2. Auth

**POST `/auth/register/`**
```json
// request
{ "email": "sam@example.com", "password": "correct horse battery", "display_name": "Sam" }
// 201
{ "user": { "id": 12, "email": "sam@example.com", "display_name": "Sam", "is_staff": false,
            "preferences": { "text_scale": 1, "reduced_motion": false, "theme": "dark", "show_tips": true } },
  "claimed": { "playthroughs": [], "conflicts": [] } }
```
Errors: 400 `validation_error` (duplicate email, weak password).

**POST `/auth/login/`**: `{ email, password }` → 200 `{ user, claimed }` · 400 `invalid_credentials` · 429 `rate_limited`.

**Claiming guest progress (D-01).** Register and login responses both include `claimed`, which describes any guest progress moved into the account:
```json
"claimed": {
  "playthroughs": [ { "id": "6c1e…", "case": "the-missing-masterpiece", "status": "in_progress" } ],
  "conflicts": [ { "case": "the-missing-masterpiece", "kept": "6c1e…", "abandoned": "91aa…" } ]   // D-23 rule
}
```
`claimed` is `{ "playthroughs": [], "conflicts": [] }` when there was no guest progress.

**GET `/auth/me/`**
```json
{ "user": { … } , "guest": null }                                             // account holder
{ "user": null,  "guest": { "has_progress": true, "expires_after_days": 90 } }  // guest (D-22)
{ "user": null,  "guest": null }                                              // fresh visitor
```

## 3. Cases

**GET `/cases/?difficulty=standard&tag=theft&status=in_progress&sort=newest`**
```json
{
  "results": [
    {
      "slug": "the-missing-masterpiece",
      "title": "The Missing Masterpiece",
      "tagline": "A priceless painting vanishes during a private preview.",
      "difficulty": "standard",
      "estimated_minutes": 60,
      "tags": ["theft", "art", "locked-room"],
      "cover_image": "/static/cases/the-missing-masterpiece/9f2c….webp",
      "cover_alt": "The empty frame on the East Room wall.",
      "published_at": "2026-11-01T00:00:00Z",
      "player": { "status": "in_progress", "playthrough_id": "6c1e…", "best_tier": null }   // null for a fresh visitor
    }
  ]
}
```
`player.status` ∈ `not_started | in_progress | solved | unsolved`. `best_tier` is the highest tier across solved playthroughs. `player` is `null` for a fresh visitor, and the `status` filter is ignored for them. No pagination in v1.0 (the case count is small); add cursor pagination if the count exceeds 50.

**GET `/cases/{slug}/`**
```json
{
  "slug": "the-missing-masterpiece",
  "title": "…", "tagline": "…", "difficulty": "standard", "estimated_minutes": 60,
  "content_notes": [],
  "setting": { "world_date": "2026-03-13", "era_note": "Present day, London." },
  "briefing": "On the evening of Friday 13 March…",
  "objective": "Determine who took the painting…",
  "starting_people": [ { "key": "vivian-ashcombe", "name": "Vivian Ashcombe", "role": "Gallery owner", "portrait": "…" } ],
  "player": { "status": "not_started", "playthrough_id": null, "history": [] },
  "copyright": "© 2026 Avnish Ozarkar. All rights reserved."
}
```
`starting_people` contains only persons whose condition is `start`. Draft and retired cases return 404 to non-staff (retired cases stay reachable via a player's own playthrough).

## 4. Playthroughs

**POST `/cases/{slug}/playthroughs/`** (`{ "restart": false }`)
- If an `in_progress` playthrough exists and `restart` is false → 200 with it.
- If `restart` is true → the existing one becomes `abandoned` and a new one is created → 201.
- Otherwise → 201 new.
- Starting a playthrough on a **retired** case → 409 `case_not_available`. Existing playthroughs of retired cases stay viewable.
```json
{ "id": "6c1e…", "case": "the-missing-masterpiece", "status": "in_progress",
  "started_at": "…", "last_active_at": "…", "content_version": 1 }
```

**GET `/playthroughs/{id}/casefile/`**: the complete player view. Only discovered items are present.
```json
{
  "playthrough": { "id": "6c1e…", "status": "in_progress", "case": { "slug": "…", "title": "…", "world_date": "2026-03-13" } },
  "people": [
    { "key": "corinne-blake", "name": "Corinne Blake", "role": "Senior Curator", "is_suspect": true,
      "summary": "…", "bio": "…", "portrait": "…", "portrait_alt": "…", "marker": 2,
      "new": false }
  ],
  "locations": [ { "key": "main-hall", "name": "The Main Hall", "description": "…", "image": "…", "visited": true, "new": false } ],
  "evidence": [
    { "key": "alarm-log", "title": "Alarm System Event Log", "kind": "record", "summary": "…",
      "body": "…", "image": null, "location": "security-office", "people": ["daniel-reyes"],
      "examined": true, "new": false, "discovered_at": "…" }
  ],
  "topics": [ { "person": "corinne-blake", "key": "her-talk", "prompt": "Ask about her talk in the Main Hall.", "asked": true } ],
  "statements": [
    { "ref": "corinne-blake/at-lectern", "person": "corinne-blake", "text": "I was at the lectern from half past nine until ten. Ask anyone.",
      "context": { "type": "topic", "key": "her-talk" },
      "claim": { "from": "2026-03-13T21:30", "to": "2026-03-13T22:00", "location": "main-hall" } }
  ],
  "timeline": [
    { "key": "talk-scheduled", "title": "Curator's talk (as scheduled)", "from": "2026-03-13T21:30", "to": "2026-03-13T22:00",
      "location": "main-hall", "people": ["corinne-blake"], "certainty": "claimed",
      "source": { "type": "evidence", "key": "event-programme" } }
  ],
  "contradictions": [                                    // confirmed only
    { "key": "lectern-photo", "statement": "corinne-blake/at-lectern",
      "conflicts_with": { "type": "evidence", "key": "guest-photo" },
      "explanation": "…", "found_at": "…" }
  ],
  "flags": [                                             // the player's own flags (D-03)
    { "id": "f1…", "statement": "corinne-blake/at-lectern", "conflicts_with": { "type": "evidence", "key": "guest-photo" },
      "status": "confirmed", "contradiction": "lectern-photo" },
    { "id": "f2…", "statement": "felix-okafor/no-pickup-booked", "conflicts_with": { "type": "evidence", "key": "courier-booking" },
      "status": "unconfirmed", "contradiction": null }
  ],
  "hints": { "available": true, "revealed_count": 1 },  // summary only; texts via /hints/
  "presented": [ { "person": "daniel-reyes", "evidence": "camera-gap", "reaction": "authored" } ],   // "authored" | "default"; lets the UI mark "no reaction" pairings
  "feed": [                                              // discovery feed (Overview), newest first, built from PlaythroughEvent
    { "at": "…", "action": { "type": "visit_location", "location": "security-office" },
      "discovered": [ { "type": "evidence", "key": "alarm-log" }, { "type": "evidence", "key": "camera-gap" } ] }
  ],
  "stats": { "contradictions_confirmed": 1, "hints_revealed": 1 }   // no incorrect-flag count (D-03)
}
```
- `body` is included for every discovered evidence item (discovered ≠ examined; examining is a recorded action that may unlock things).
- **No totals** of undiscovered items are ever included (PRODUCT_SPEC §7.3).
- For **staff preview playthroughs only**, each item also carries `requires` (its unlock condition) to support "Show unlock reasons".

### 4.1 Actions

**POST `/playthroughs/{id}/actions/`**

| `type` | Body fields | Precondition (else 422 `action_unavailable`) |
|---|---|---|
| `visit_location` | `location` | location discovered |
| `examine_evidence` | `evidence` | evidence discovered |
| `ask_topic` | `person`, `topic` | topic available |
| `present_evidence` | `person`, `evidence` | both discovered |

Response (200):
```json
{
  "action": { "type": "ask_topic", "person": "corinne-blake", "topic": "her-talk" },
  "repeat": false,
  "result": {
    "statements": ["corinne-blake/at-lectern"]          // present_evidence/ask_topic
    // visit_location:   { "location": "main-hall" }
  },
  "discovered": {                                        // same item shapes as the casefile, new items only
    "statements": [ { "ref": "corinne-blake/at-lectern", … } ],
    "timeline": [ … ], "evidence": [], "topics": [], "people": [], "locations": [], "contradictions": []
  }
}
```
- A `present_evidence` with no authored reaction returns the person's `default_reaction` as a non-citable line: `"result": { "statements": [], "default_reaction": "…" }`.
- 409 `playthrough_not_in_progress` once the playthrough is accused, abandoned, or stale.

**POST `/playthroughs/{id}/seen/`** `{ "items": [{ "type": "evidence", "key": "alarm-log" }] }` → 204.

**POST `/playthroughs/{id}/heartbeat/`** `{ "seconds": 30 }`: sent every 30 s while the tab is visible. The server caps each heartbeat at 60 s → 204.

### 4.2 Contradiction flags (D-03)

**POST `/playthroughs/{id}/flags/`**
```json
// request
{ "statement": "corinne-blake/at-lectern", "conflicts_with": { "type": "evidence", "key": "guest-photo" } }
// 201: correct pairing (either order, or an `accept_also` alternative)
{ "flag": { "id": "f1…", "status": "confirmed", "contradiction": "lectern-photo", … },
  "explanation": "The guest's photo, time-stamped 21:51, shows the lectern empty…",
  "discovered": { "topics": [ { "person": "corinne-blake", "key": "the-intermission", … } ], "evidence": [ { "key": "dismissal-draft", … } ], … } }
// 201: incorrect pairing (saved as unconfirmed, with no penalty and no information leaked)
{ "flag": { "id": "f2…", "status": "unconfirmed", "contradiction": null, … }, "explanation": null, "discovered": {} }
```
- 422 `action_unavailable` if either side isn't discovered. 409 `flag_exists` (with the existing flag) if this exact pairing is already flagged.
- 409 `playthrough_not_in_progress` after accusation.

**PATCH `/playthroughs/{id}/flags/{flagId}/`**: revise an unconfirmed flag by changing either side, `{ "statement"?: …, "conflicts_with"?: … }`. The server re-verifies, and the response has the same shape as POST. 409 `flag_locked` if the flag is already confirmed.

**DELETE `/playthroughs/{id}/flags/{flagId}/`** → 204 for unconfirmed flags. 409 `flag_locked` for confirmed ones (D-24 default).

### 4.3 Hints (D-04)

**GET `/playthroughs/{id}/hints/`**
```json
{
  "tracks": [
    { "key": "test-curator-alibi", "goal": "Test the curator's account of the evening.",
      "revealed": [ { "tier": 1, "level": "nudge", "text": "Corinne was confident…" } ],
      "next_tier": "pointer", "resolved": false }
  ],
  "suggested": "test-curator-alibi"
}
```
- `tracks` lists only **offered** tracks (relevant, unresolved) plus any track with revealed tiers, so earlier hints stay readable after a track resolves (`"resolved": true`).
- An offered track's `goal` appears here before any tier is revealed. Unrevealed tier text never does.
- `next_tier` is `null` once all 3 tiers are revealed.

**POST `/playthroughs/{id}/hints/`** `{ "track": "test-curator-alibi" }` (optional; defaults to `suggested`) → 201 `{ "track": "…", "tier": 2, "level": "pointer", "text": "…" }`.
- Tier 3 (`direction`) requires `"confirm": true`, otherwise 400 `confirmation_required`. The UI shows a confirm step.
- 409 `no_hint_available` if no track is offered or the track has no further tiers.

## 5. Board, notes, theories, markers

**PUT `/playthroughs/{id}/board/`**
```json
// request
{ "version": 7, "layout": { "cards": [ … ], "links": [ … ] } }   // shape in DATA_MODEL §5
// 200
{ "version": 8, "layout": { … } }
```
409 `version_conflict` returns the current `{ version, layout }` so the client can offer a reload. 400 `invalid_reference` if a card references an undiscovered item.

**POST `/playthroughs/{id}/notes/`**: `{ "body": "Programme says the talk ran to ten…", "attached": { "type": "evidence", "key": "event-programme" } }` → 201 `{ id, body, attached, version, created_at, updated_at }`.
**PATCH** requires `version`. A stale version → 409.

**POST `/playthroughs/{id}/theories/`**
```json
{ "title": "The curator did it", "suspect": "corinne-blake",
  "opportunity": "Left the lectern during the intermission",
  "method": "Bypassed the sensor using the maintenance override",
  "motive": "Unknown — check Vivian's office",
  "open_questions": "Where is the canvas?",
  "supporting": [ { "type": "evidence", "key": "guest-photo" } ],
  "status": "active" }
```
→ 201 with `id` and `version`. Theories are never evaluated by the server.

**PUT `/playthroughs/{id}/markers/{personKey}/`**: `{ "level": 3 }` → 204.

## 6. Accusation & results

**Investigation review (D-02).** The review screen before the accusation is built client-side from data the workspace already has: the casefile (confirmed contradictions, unconfirmed flags, suspicion markers, loose ends: unexamined evidence, unasked topics, unvisited locations), the theories list (active theory), and the board (pinned items). It needs no extra endpoint and reveals nothing new.

**GET `/playthroughs/{id}/accusation-form/`**
```json
{
  "intro": "Present your case. This is final.",
  "attempts_remaining": 1,                // always 1 before submission (D-02)
  "questions": [
    { "key": "culprit", "prompt": "Who took the painting?", "kind": "person",
      "options": [ { "key": "corinne-blake", "label": "Corinne Blake" }, … ],   // discovered suspects only
      "cite": { "min": 0, "max": 0 } },
    { "key": "method", "prompt": "How was the painting removed without the alarm?", "kind": "choice",
      "options": [ { "key": "override-bypass", "label": "A maintenance override bypassed the East Room sensor." }, … ],
      "cite": { "min": 1, "max": 2, "prompt": "Cite the evidence that proves the method." } }
  ]
}
```
`required_for_solve` is **not** exposed. Exposing it would hint at which questions matter.

**POST `/playthroughs/{id}/accusation/`**
```json
// request
{ "answers": {
    "culprit":      { "answer": "corinne-blake", "cite": [] },
    "opportunity":  { "answer": "during-intermission", "cite": [ { "type": "evidence", "key": "guest-photo" } ] },
    "method":       { "answer": "override-bypass", "cite": [ { "type": "evidence", "key": "alarm-log" } ] },
    "motive":       { "answer": "dismissal-and-buyer", "cite": [ { "type": "statement", "key": "corinne-blake/buyer-admission" } ] },
    "location-now": { "answer": null, "cite": [ { "type": "evidence", "key": "return-crate" } ] } },
  "confirm": true }
// 201
{ "outcome": "solved", "tier": "airtight", "score": 95, "max_score": 100, "results_url": "/api/v1/playthroughs/6c1e…/results/" }
```
Validation: every question answered, options valid, citation counts within `min..max`, and `confirm: true` (400 `validation_error`). Every citation must be discovered by this playthrough (400 `invalid_reference`). In this example, motive cites only a partial proof set, so it scores 15/20 and the total is 95. 409 `accusation_already_submitted` (D-02).
Effect: the accusation is stored and frozen, and the playthrough becomes `accused`.

**GET `/playthroughs/{id}/results/`** (409 `results_unavailable` before accusation)
```json
{
  "outcome": "solved", "tier": "airtight", "score": 95, "max_score": 100,
  "breakdown": [
    { "question": "method", "prompt": "…", "your_answer": "override-bypass", "correct_answer": "override-bypass",
      "correct": true, "answer_points": 10,
      "proof": { "earned": 10, "max": 10, "your_citations": [ … ], "accepted": [ [ … ] ] },
      "earned": 20, "max": 20, "explanation": "…" }
  ],
  "solution": { "summary": "…", "narrative": "…" },
  "red_herrings": [ { "person": "vivian-ashcombe", "suspicion": "…", "cleared_by": [ … ], "explanation": "…", "you_found_clearing_evidence": true } ],
  "contradictions": [ { "key": "lectern-photo", "found": true, "statement": "…", "conflicts_with": { … }, "explanation": "…" } ],
  "missed_key_evidence": [ { "key": "cotton-gloves", "title": "…", "summary": "…" } ],
  "hints_used": [ { "track": "where-did-it-go", "goal": "…", "tiers_revealed": 2 } ],
  "stats": { "active_minutes": 54, "evidence_found": 19, "evidence_total": 24, "contradictions_confirmed": 2, "contradictions_total": 3, "hints_revealed": 2 }
}
```
After accusation, results may include totals and undiscovered content (it's the reveal).

## 7. Progress

**GET `/me/progress/`**
```json
{
  "identity": "account",            // "account" | "guest"; guests see only this browser's playthroughs, plus a save prompt
  "totals": { "cases_available": 3, "solved": 1, "unsolved": 0, "in_progress": 1, "airtight": 1, "active_minutes": 54 },
  "cases": [
    { "slug": "the-missing-masterpiece", "title": "…", "status": "solved", "best_tier": "airtight",
      "playthroughs": [ { "id": "6c1e…", "status": "accused", "outcome": "solved", "tier": "airtight", "started_at": "…", "accused_at": "…" } ] }
  ]
}
```

## 8. Frontend consumption

- **Typed client**: `npm run api:types` runs `openapi-typescript` against the generated schema → `src/api/schema.d.ts`. Endpoint wrappers in `src/api/endpoints/*.ts` are small typed functions over a shared `request()` in `src/api/client.ts`.
- `client.ts`:
  - calls `GET /auth/csrf/` once on boot; reads the `csrftoken` cookie; sets `X-CSRFToken` on unsafe methods;
  - sends `credentials: 'same-origin'`;
  - parses the error envelope into `ApiError { status, code, message, details }`;
  - on 401 (account-only endpoints), clears the account state and redirects to `/login?next=…`. Guests never hit 401 during play.
- **Stores**:

| Store | Endpoints |
|---|---|
| `auth` | `/auth/*`, `/me/profile/`, `/me/password/`, `/me/guest/`; holds user-or-guest state and the last claim result |
| `library` | `/cases/`, `/cases/{slug}/` |
| `playthrough` | `casefile`, `actions`, `flags`, `seen`, `heartbeat`, `markers`, `abandon` |
| `hints` | `hints` (GET lazily, POST to reveal) |
| `board` | `board` (debounced PUT, version tracking) |
| `notes`, `theories` | CRUD with optimistic updates + version |
| `accusation` | `accusation-form`, `accusation`, `results` |
| `progress` | `/me/progress/` |

- **Action flow**: `useAction()` composable → `POST actions` → merge `discovered` into the `playthrough` store → emit a discovery toast → disable the triggering control while the request is pending (prevents double submits).
- **Loading strategy**: the workspace loads `casefile` once and never re-fetches per tab. Results and progress are fetched on navigation.

## 9. Error codes

`validation_error`, `invalid_credentials`, `not_authenticated`, `csrf_failed`, `permission_denied`, `not_found`, `rate_limited`, `playthrough_not_in_progress`, `action_unavailable`, `invalid_reference`, `version_conflict`, `flag_exists`, `flag_locked`, `no_hint_available`, `confirmation_required`, `accusation_already_submitted`, `results_unavailable`, `case_not_available`, `server_error`.

## 10. Rate limits (initial)

| Scope | Limit |
|---|---|
| login / register / password reset | 10 / min / IP, 5 / min / account |
| starting playthroughs (guests) | 10 / hour / IP |
| actions + flags | 120 / min / player |
| hint reveals | 30 / min / player |
| board / notes / theories writes | 60 / min / player |
| everything else | 300 / min / player |

"Player" here means user ID for account holders and guest ID for guests.
