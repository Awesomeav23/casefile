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
                 ├─* 🔒HintTrack 1─3 🔒Hint
                 └─* CaseImport (audit)

play:      (User | guest_id) 1─* Playthrough *─1 Case
                    ├─* PlaythroughEvent  (append-only action log)
                    ├─* Fact              (deduplicated successful actions)
                    ├─* Discovery         (what the player has found)
                    ├─* ContradictionFlag (player flags: unconfirmed | confirmed)
                    ├─* HintReveal        (hint tiers the player requested)
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
| copyright | varchar(200) | not null; content copyright line (CASE_DESIGN §7.1, D-20) |
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
| location_id | FK → location | nullable, `RESTRICT` (a location can't be deleted while evidence uses it, but deleting the whole case still cascades) |
| image, image_alt | varchar | check: alt not empty when image set |
| requires | jsonb | stored **effective** condition (implicit `visited` already combined by importer). Every `requires` column stores the effective condition (people, locations, topics with their person, timeline events with their source) |
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
| claim_from, claim_to | timestamptz | nullable; in-world wall-clock time stored as UTC (the zone has no meaning) |
| claim_location_id | FK → location | nullable |
| sort_order | integer | |
| | | **check: exactly one of (topic_id, reaction_evidence_id) is not null** |
| | | check: claim_to ≥ claim_from |

### `content_timelineevent`
| Field | Type | Constraints |
|---|---|---|
| case_id, key | | **unique (case_id, key)** |
| title, description | | |
| starts_at | timestamptz | not null; in-world wall-clock time stored as UTC |
| ends_at | timestamptz | nullable; check ≥ starts_at |
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
`case_id`, `imported_at`, `imported_by` (varchar: CLI user), `content_hash`, `content_version`, `breaking` bool, `report` jsonb (`warnings`, `breaking` reasons, and `published: true` for publish-only imports). One row per import that changed something; unchanged re-imports write none.

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
`case_id` (**unique**, 1:1), `summary`, `narrative`, `key_evidence` text[] (evidence keys), `walkthrough` jsonb (used by tests and staff preview), `answer_terms` text[] (giveaway phrases for hint lint F14).

### `content_hinttrack` 🔒
| Field | Type | Constraints |
|---|---|---|
| case_id, key | | **unique (case_id, key)** |
| goal | varchar(120) | player-facing label, shown once offered |
| priority | smallint | default 100; lower is offered first |
| requires | jsonb | when the track becomes relevant |
| resolved_when | jsonb | when it stops being offered |
| mentions | jsonb | citation refs named in any tier (validator F12) |

### `content_hint` 🔒
`track_id` FK → hinttrack (`CASCADE`), `tier` smallint (check 1–3), `level` varchar (check in `nudge`,`pointer`,`direction`; must match tier 1/2/3), `text`. **unique (track_id, tier)**. The importer requires exactly 3 tiers per track.

### `content_redherring` 🔒
`case_id`, `person_id` (**unique (case_id, person_id)**), `suspicion`, `cleared_by` jsonb (refs), `explanation`.

## 5. Play (per-player state)

### `play_playthrough`
| Field | Type | Constraints / notes |
|---|---|---|
| id | uuid | PK |
| user_id | FK → user | nullable: null for guest-owned playthroughs (D-01); `CASCADE` |
| guest_id | uuid | nullable: the guest identity stored in the anonymous session (ARCHITECTURE §5); set to null when claimed |
| case_id | FK → case | `PROTECT` (cases are retired, not deleted) |
| content_version | integer | version at start |
| status | varchar | check in (`in_progress`,`accused`,`abandoned`,`stale`) |
| started_at, last_active_at | timestamptz | |
| accused_at | timestamptz | nullable |
| active_seconds | integer | accumulated from client heartbeats, capped per interval |
| is_preview | bool | default false; staff preview playthroughs (reveal-all, `requires` exposure); excluded from progress and statistics |
| | | **check: exactly one of (user_id, guest_id) is not null** |
| | | **partial unique (user_id, case_id) WHERE status = 'in_progress' AND NOT is_preview**: one active investigation per case per account |
| | | **partial unique (guest_id, case_id) WHERE status = 'in_progress'**: one per case per guest |
| | | index (user_id, last_active_at desc); index (guest_id, last_active_at) (purge job, D-22) |

### `play_playthroughevent` (append-only log)
| Field | Type | Notes |
|---|---|---|
| id | bigint | PK |
| playthrough_id | FK | `CASCADE`; index (playthrough_id, id) |
| type | varchar | `visit_location`, `examine_evidence`, `ask_topic`, `present_evidence`, `flag_created`, `flag_revised`, `flag_removed`, `hint_revealed`, `accuse`, `abandon`, `claimed` |
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

### `play_contradictionflag` (D-03)
| Field | Type | Constraints |
|---|---|---|
| id | uuid | PK |
| playthrough_id | FK | `CASCADE` |
| statement_key | varchar(161) | the flagged statement |
| conflicts_type | varchar | check in (`evidence`,`statement`) |
| conflicts_key | varchar(161) | |
| status | varchar | check in (`unconfirmed`,`confirmed`) |
| contradiction_key | varchar(80) | null unless confirmed |
| revision | smallint | incremented on each revise |
| | | **unique (playthrough_id, statement_key, conflicts_type, conflicts_key)** (the same pairing can't be flagged twice) |
| | | **partial unique (playthrough_id, contradiction_key) WHERE status = 'confirmed'** |
| | | check: `contradiction_key IS NOT NULL` ⇔ `status = 'confirmed'` |

Unconfirmed flags may be revised (pairing changed, then re-verified) or deleted. Confirmed flags are immutable and undeletable, and their `contradiction` fact is permanent (D-24 covers hiding them). Incorrect attempts aren't counted anywhere player-facing (D-03). The event log keeps them for debugging only.

### `play_hintreveal` (D-04)
`playthrough_id` FK (`CASCADE`), `track_key` varchar(80), `tier` smallint (check 1–3), `revealed_at`. **unique (playthrough_id, track_key, tier)**. Check in service: tier *n* requires tier *n−1* already revealed.

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
| playthrough_id | FK | **unique**: exactly one final accusation per playthrough (D-02). Replay = a new playthrough |
| answers | jsonb | `{ "<question_key>": { "answer": "...", "cite": [ref, …] } }` |
| score, max_score | smallint | |
| outcome | varchar | check in (`solved`,`unsolved`) |
| tier | varchar | check in (`airtight`,`convincing`,`shaky`) or null when unsolved |
| breakdown | jsonb | per-question result, frozen at submission |
| stats | jsonb | frozen statistics (time, % evidence found, contradictions confirmed, hints used per tier); incorrect flags not included (D-03) |
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

- **Account deletion** cascades to profile, playthroughs, events, facts, discoveries, flags, hint reveals, notes, board, theories, markers, and accusations.
- **Guest data** (D-22): `purge_guest_data` deletes guest-owned playthroughs (and their cascades) whose `last_active_at` is older than the retention period (default 90 days). "Forget my progress on this browser" deletes the current guest's playthroughs immediately.
- **Claiming** (D-01, D-23): on login/register, guest playthroughs get `user_id` set and `guest_id` cleared in one transaction. If an in-progress conflict hits the account's partial unique index, the less recently active playthrough is marked `abandoned` first (D-23).
- Cases are never hard-deleted once published; they move to `retired` (hidden from the library, but still viewable in a player's history).
- Data export (PRODUCT_SPEC §5.1) serializes the user's playthrough tables to JSON.

## 9. Flexibility for different mystery formats

- Accusation questions are data, so a case can ask "who", "how", "why", "where is it", "who was the accomplice", or "which document is forged" without schema changes.
- Persons distinguish suspects from witnesses with one flag. A case can have multiple culprits if its accusation uses two `person` questions.
- Evidence `kind` is a closed list rendered by the frontend. Adding a kind is a small code change (ARCHITECTURE §8).
- Hints (D-04) are per-case content (`content_hinttrack`, `content_hint`). A case can have any number of tracks, and track relevance uses the same condition language as discovery.
