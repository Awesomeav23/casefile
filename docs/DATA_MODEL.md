# Casefile: Data Model

**Status:** Planning draft. Proposed PostgreSQL schema via Django models. No migrations exist yet.
**Related:** [CASE_DESIGN](CASE_DESIGN.md) (authoring format these tables store) · [ARCHITECTURE](ARCHITECTURE.md) · [API_PLAN](API_PLAN.md)

Conventions:
- Django-managed tables. `id` is a `bigint` identity unless noted. Player-owned rows that appear in URLs use `uuid` primary keys.
- `created_at` / `updated_at` (`timestamptz`) on all mutable tables; omitted below for brevity.
- **Content keys** (`key`) are author-defined stable slugs from the YAML (CASE_DESIGN §3).
- `requires` columns hold the parsed condition expression as **JSONB** (CASE_DESIGN §4).
- 🔒 marks **spoiler tables**: read only by the scoring/results services, never by player serializers.

---

## 1. Entity overview

```
accounts:  User 1─1 PlayerProfile

content:   Case 1─* Person ─┬─* Topic ─* Statement
                 │          └─* Statement (reaction, via Evidence)
                 ├─* Location 1─* Evidence *─* Person
                 ├─* TimelineEvent *─* Person
                 ├─* AccusationQuestion 1─* AccusationOption
                 ├─* 🔒Contradiction
                 ├─1 🔒CaseSolution
                 ├─* 🔒RedHerring
                 ├─* 🔒AnswerKey (1─1 AccusationQuestion)
                 └─* CaseImport (audit)

play:      User 1─* Playthrough *─1 Case
                    ├─* PlaythroughEvent  (append-only action log)
                    ├─* Fact              (deduplicated successful actions)
                    ├─* Discovery         (what the player has found)
                    ├─* Note
                    ├─1 Board
                    ├─* Theory
                    ├─* PersonMarker
                    └─0..1 Accusation
```

## 2. Accounts

### `accounts_user` (custom user model)
| Field | Type | Constraints |
|---|---|---|
| id | bigint | PK |
| email | citext / varchar(254) | **unique** (case-insensitive) |
| password | varchar | Argon2 hash |
| is_active, is_staff, is_superuser | bool | |
| date_joined, last_login | timestamptz | |

### `accounts_playerprofile`
| Field | Type | Constraints |
|---|---|---|
| user_id | FK → user | PK, `ON DELETE CASCADE` |
| display_name | varchar(40) | not null |
| preferences | jsonb | default `{}`: `{ text_scale, reduced_motion, theme, show_tips }` |

## 3. Content (player-visible once discovered)

### `content_case`
| Field | Type | Constraints / notes |
|---|---|---|
| id | bigint | PK |
| slug | varchar(80) | **unique**, immutable once published |
| title, tagline | varchar | not null |
| difficulty | varchar | check in (`introductory`,`standard`,`hard`) |
| estimated_minutes | smallint | > 0 |
| tags | text[] | GIN index |
| content_notes | text[] | |
| world_date | date | |
| era_note | text | |
| cover_image, cover_alt | varchar | |
| briefing, objective | text | Markdown |
| accusation_intro | text | |
| rating_thresholds | jsonb | nullable → global defaults |
| status | varchar | check in (`draft`,`published`,`retired`); index |
| format_version | smallint | |
| content_version | integer | incremented on breaking re-import (ARCHITECTURE §8) |
| content_hash | char(64) | sha256 of the source folder; skips no-op imports |
| sort_order | integer | |
| published_at | timestamptz | nullable |

### `content_person`
| Field | Type | Constraints |
|---|---|---|
| case_id | FK → case | `CASCADE` |
| key | varchar(80) | **unique (case_id, key)** |
| name, role, summary | varchar | |
| bio, default_reaction | text | |
| is_suspect | bool | index (case_id, is_suspect) |
| portrait, portrait_alt | varchar | nullable; check: alt not empty when portrait set |
| requires | jsonb | |
| sort_order | integer | |

### `content_location`
`case_id`, `key` (**unique (case_id, key)**), `name`, `description`, `image`, `image_alt`, `requires` jsonb, `sort_order`.

### `content_evidence`
| Field | Type | Constraints |
|---|---|---|
| case_id | FK → case | |
| key | varchar(80) | **unique (case_id, key)** |
| title, summary | varchar | |
| kind | varchar | check in (`document`,`photo`,`object`,`record`,`correspondence`,`transcript`) |
| body | text | |
| location_id | FK → location | nullable, `PROTECT` |
| image, image_alt | varchar | check: alt not empty when image set |
| requires | jsonb | stored **effective** condition (implicit `visited` already combined by importer) |
| sort_order | integer | |

`content_evidence_people`: M2M (evidence_id, person_id), unique pair.

### `content_topic`
`case_id`, `person_id` FK, `key` (**unique (person_id, key)**), `prompt`, `requires` jsonb, `sort_order`.

### `content_statement`
| Field | Type | Constraints |
|---|---|---|
| case_id | FK | |
| person_id | FK → person | |
| key | varchar(80) | **unique (person_id, key)** |
| text | text | |
| topic_id | FK → topic | nullable |
| reaction_evidence_id | FK → evidence | nullable |
| claim_from, claim_to | timestamp (no tz) | nullable; in-world wall-clock |
| claim_location_id | FK → location | nullable |
| sort_order | integer | |
| | | **check: exactly one of (topic_id, reaction_evidence_id) is not null** |
| | | check: claim_to ≥ claim_from |

### `content_timelineevent`
| Field | Type | Constraints |
|---|---|---|
| case_id, key | | **unique (case_id, key)** |
| title, description | | |
| starts_at | timestamp (no tz) | not null |
| ends_at | timestamp (no tz) | nullable; check ≥ starts_at |
| location_id | FK | nullable |
| certainty | varchar | check in (`claimed`,`verified`) |
| source_evidence_id | FK → evidence | nullable |
| source_statement_id | FK → statement | nullable |
| requires | jsonb | not null |
| | | **check: exactly one source set** |

`content_timelineevent_people`: M2M. Index `(case_id, starts_at)`.

### `content_accusationquestion`
`case_id`, `key` (**unique (case_id, key)**), `prompt`, `kind` (check in `person`,`choice`,`evidence`), `required_for_solve` bool, `cite_min`, `cite_max` (check `0 ≤ cite_min ≤ cite_max ≤ 5`), `cite_prompt`, `sort_order`.

### `content_accusationoption`
`question_id` FK, `key` (**unique (question_id, key)**), `label`, `sort_order`. Only for `choice` questions (enforced by the importer).

### `content_caseimport` (audit)
`case_id`, `imported_at`, `imported_by` (varchar: CLI user), `content_hash`, `content_version`, `breaking` bool, `report` jsonb (validator output).

## 4. Spoiler tables 🔒

### `content_contradiction` 🔒
| Field | Type | Constraints |
|---|---|---|
| case_id, key | | **unique (case_id, key)** |
| statement_id | FK → statement | not null |
| conflicts_evidence_id | FK → evidence | nullable |
| conflicts_statement_id | FK → statement | nullable |
| accept_also | jsonb | list of alternative `{evidence|statement}` refs |
| explanation | text | shown once found |
| | | **check: exactly one of conflicts_evidence_id / conflicts_statement_id** |

### `content_answerkey` 🔒
| Field | Type | Constraints |
|---|---|---|
| question_id | FK → accusationquestion | **unique** (1:1) |
| correct_value | varchar | person key or option key; null for `evidence`-kind |
| points | smallint | ≥ 0 |
| proof_points | smallint | ≥ 0 |
| proof_full | jsonb | list of lists of citation refs |
| proof_partial | jsonb | list of lists |
| explanation | text | |

### `content_casesolution` 🔒
`case_id` (**unique**, 1:1), `summary`, `narrative`, `key_evidence` text[] (evidence keys), `walkthrough` jsonb (used by tests and staff preview), `hints` jsonb (reserved, D-04).

### `content_redherring` 🔒
`case_id`, `person_id` (**unique (case_id, person_id)**), `suspicion`, `cleared_by` jsonb (refs), `explanation`.

## 5. Play (per-player state)

### `play_playthrough`
| Field | Type | Constraints / notes |
|---|---|---|
| id | uuid | PK |
| user_id | FK → user | nullable **only** to support guest play (D-01); `CASCADE` |
| guest_session_key | varchar(40) | nullable; unused unless D-01 approved |
| case_id | FK → case | `PROTECT` (cases are retired, not deleted) |
| content_version | integer | version at start |
| status | varchar | check in (`in_progress`,`accused`,`abandoned`,`stale`) |
| started_at, last_active_at | timestamptz | |
| accused_at | timestamptz | nullable |
| active_seconds | integer | accumulated from client heartbeats, capped per interval |
| is_preview | bool | default false; staff preview playthroughs (reveal-all, `requires` exposure); excluded from progress and statistics |
| | | **check: user_id IS NOT NULL OR guest_session_key IS NOT NULL** |
| | | **partial unique (user_id, case_id) WHERE status = 'in_progress' AND NOT is_preview** — one active investigation per case |
| | | index (user_id, last_active_at desc) |

### `play_playthroughevent` (append-only log)
| Field | Type | Notes |
|---|---|---|
| id | bigint | PK |
| playthrough_id | FK | `CASCADE`; index (playthrough_id, id) |
| type | varchar | `visit_location`, `examine_evidence`, `ask_topic`, `present_evidence`, `flag_contradiction`, `accuse`, `abandon` |
| payload | jsonb | action input, e.g. `{ "person": "...", "evidence": "..." }` |
| outcome | jsonb | e.g. `{ "correct": false }`, discovered keys |
| is_repeat | bool | true when it created no new fact |
| created_at | timestamptz | |

Never updated or deleted, except by cascade on account deletion.

### `play_fact`
`playthrough_id`, `kind` (`visited`,`examined`,`asked`,`presented`,`contradiction`), `ref` varchar (e.g. `corinne-blake/her-talk`), `event_id` FK, **unique (playthrough_id, kind, ref)**. The condition evaluator reads this table. The unique constraint makes actions idempotent.

### `play_discovery`
| Field | Type | Constraints |
|---|---|---|
| playthrough_id | FK | `CASCADE` |
| item_type | varchar | check in (`person`,`location`,`evidence`,`topic`,`statement`,`timeline_event`,`contradiction`) |
| item_key | varchar(161) | e.g. `alarm-log`, `corinne-blake/at-lectern` |
| discovered_at | timestamptz | |
| source_event_id | FK → event | nullable (null = available at start) |
| seen_at | timestamptz | nullable; drives "new" badges |
| | | **unique (playthrough_id, item_type, item_key)** |

**Why keys rather than foreign keys here:** playthrough state must survive content re-imports. Rows are upserted by key, so referring to keys keeps discoveries valid when content IDs or text change. The importer's breaking-change rule (ARCHITECTURE §8) guarantees that referenced keys aren't removed under an active playthrough. Integrity is checked in application code and by a test that cross-checks all discoveries against content.

### `play_note`
`id` uuid, `playthrough_id`, `body` text (≤ 10 000 chars), `attached_type` + `attached_key` (nullable pair; check both-or-neither), `version` int. Index (playthrough_id, updated_at).

### `play_board`
`playthrough_id` (PK, 1:1), `layout` jsonb, `version` int.
```json
{
  "cards": [{ "id": "c1", "ref": { "type": "evidence", "key": "alarm-log" }, "x": 120, "y": 80 },
            { "id": "c2", "ref": { "type": "note", "id": "b3f…" }, "x": 400, "y": 60 }],
  "links": [{ "id": "l1", "from": "c1", "to": "c2", "label": "contradicts" }]
}
```
`ref.type` is one of the `play_discovery.item_type` values (`person`, `location`, `evidence`, `statement`, `timeline_event`, `contradiction`; `topic` excluded) or `note`. Server validation: every `ref` is discovered (or an owned note). Limits are ≤ 200 cards and ≤ 400 links.

### `play_theory`
`id` uuid, `playthrough_id`, `title` varchar(80), `suspect_key` nullable, `opportunity`, `method`, `motive`, `open_questions` (text), `supporting` jsonb (list of citation refs), `status` (check in `active`,`discarded`), `version` int.

### `play_personmarker`
`playthrough_id`, `person_key`, `level` smallint (check 0–3: none / curious / suspicious / prime), **unique (playthrough_id, person_key)**.

### `play_accusation`
| Field | Type | Constraints |
|---|---|---|
| playthrough_id | FK | **unique** (one attempt, default pending D-02; if multiple attempts are approved, replace with `attempt_no` + unique (playthrough_id, attempt_no)) |
| answers | jsonb | `{ "<question_key>": { "answer": "...", "cite": [ref, …] } }` |
| score, max_score | smallint | |
| outcome | varchar | check in (`solved`,`unsolved`) |
| tier | varchar | check in (`airtight`,`convincing`,`shaky`) or null when unsolved |
| breakdown | jsonb | per-question result, frozen at submission |
| stats | jsonb | frozen statistics (time, % found, flags right/wrong) |
| content_version | integer | |
| submitted_at | timestamptz | |

Results are **frozen at submission** so later content edits don't change past scores.

## 6. Citation reference format (shared)

Used in `answers.cite`, `theory.supporting`, `answerkey.proof_*`, `redherring.cleared_by`:
```json
{ "type": "evidence", "key": "alarm-log" }
{ "type": "statement", "key": "corinne-blake/at-lectern" }
{ "type": "contradiction", "key": "lectern-photo" }
```

## 7. Integrity rules enforced in application code

| Rule | Where |
|---|---|
| All `requires` refs resolve within the case | validator / importer |
| Choice questions have ≥ 2 options; person questions have none | importer |
| Every non-evidence question has an answer key with `correct_value` | importer |
| Accusation citations must be discovered by that playthrough | scoring service |
| Board refs / theory refs / note attachments are discovered | play services |
| Discoveries reference existing content keys | importer (breaking-change guard) + test |

## 8. Deletion and retention

- **Account deletion** cascades to profile, playthroughs, events, facts, discoveries, notes, board, theories, markers, and accusations.
- Cases are never hard-deleted once published; they move to `retired` (hidden from the library, but still viewable in a player's history).
- Data export (PRODUCT_SPEC §5.1) serializes the user's playthrough tables to JSON.

## 9. Flexibility for different mystery formats

- Accusation questions are data, so a case can ask "who", "how", "why", "where is it", "who was the accomplice", or "which document is forged" without schema changes.
- Persons distinguish suspects from witnesses with one flag. A case can have multiple culprits if its accusation uses two `person` questions.
- Evidence `kind` is a closed list rendered by the frontend. Adding a kind is a small code change (ARCHITECTURE §8).
- Hints (D-04) are reserved in `casesolution.hints`. Using them would add a `hint_used` event type and require no new tables.
