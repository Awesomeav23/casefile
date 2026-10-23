# Casefile: Case Design Standards

**Status:** Format v1 is implemented and enforced by `manage.py validate_case` (M3). The importer arrives in M4. The *Missing Masterpiece* folder is a validating skeleton, and the full content comes in M17.
**Related:** [PRODUCT_SPEC](PRODUCT_SPEC.md) · [DATA_MODEL](DATA_MODEL.md) · [ARCHITECTURE](ARCHITECTURE.md) · [TESTING_PLAN](TESTING_PLAN.md)

This document defines how a mystery is structured, written, and validated so that **adding a case is a content task, not a coding task**. It uses *The Missing Masterpiece* as a worked example. That case is one of several planned cases, not the whole application.

> ⚠️ **Spoiler layout.** §1–§8 define the format. The code snippets in §5 use fragments of the example case, so **§5.5, §5.8, §5.9, and §5.10 contain partial spoilers**. The full player-visible example is in §9. The complete solution appears only in [§10 Spoiler section](#10-spoiler-section-the-missing-masterpiece-solution). In real case folders, spoilers live only under `spoilers/`.

---

## 1. Core concepts

| Concept | Definition |
|---|---|
| **Case** | One self-contained mystery: metadata, briefing, content, accusation form, solution. |
| **Person** | Any character. A person is a *suspect* if they can be chosen as culprit. Others are witnesses or background figures. |
| **Location** | A place the player can visit. Visiting reveals the evidence found there. |
| **Evidence** | A discoverable item: document, photograph, object, record, correspondence, or transcript. |
| **Topic** | A subject the player can ask a specific person about. |
| **Statement** | One recorded line a person says, in answer to a topic or a presented piece of evidence. Statements are citable. |
| **Reaction** | The statements a person gives when shown a specific evidence item. |
| **Timeline event** | Something that happened at a time and place, either *claimed* (from a statement) or *verified* (from evidence). |
| **Contradiction** | An authored conflict between a statement and an evidence item (or between two statements). Players must find and flag it. *Spoiler content.* |
| **Hint track** | An authored line of help tied to one investigative goal (e.g. "Test the curator's alibi"), with three tiers of increasing specificity. *Spoiler content, revealed on request.* |
| **Unlock condition** (`requires`) | A rule that controls when an item becomes discovered or available. |
| **Accusation form** | The questions the player answers to close the case. Player-visible. |
| **Answer key & solution** | Correct answers, accepted proof, and the explanation. *Spoiler content.* |

### Facts and discovery

Each player action creates a **fact**: `visited`, `examined`, `asked`, `presented`, `contradiction`. After every action the discovery engine re-checks all `requires` conditions and adds any newly satisfied items to the player's casefile. Conditions are **monotonic**: there is no `not`, and facts are never removed. So:

- Once discovered, content stays discovered.
- A case can never become unwinnable.
- Solvability can be proven by running every possible action until nothing new appears (see §8).

## 2. Case folder layout

```
content/cases/<slug>/
├── case.yaml            # metadata, briefing, settings           (player-visible)
├── people.yaml          # persons                                (player-visible)
├── locations.yaml       # locations                              (player-visible)
├── evidence.yaml        # evidence items                         (player-visible)
├── interviews.yaml      # topics, statements, reactions          (player-visible)
├── timeline.yaml        # timeline events                        (player-visible)
├── accusation.yaml      # accusation questions & options         (player-visible)
├── spoilers/
│   ├── contradictions.yaml   # authored contradictions           (SPOILER)
│   ├── hints.yaml            # tiered hint tracks                (SPOILER; revealed one tier at a time on request)
│   └── solution.yaml         # answer key, solution, red herrings, walkthrough (SPOILER)
└── assets/
    ├── cover.webp
    ├── people/<person-key>.webp
    ├── locations/<location-key>.webp
    └── evidence/<evidence-key>.webp
```

"Player-visible" means the content *may* be shown to a player **once discovered**. Nothing is sent to a client before it's discovered (PRODUCT_SPEC §7.3). Everything under `spoilers/` is shown only on the results screen, with two exceptions:
- a contradiction's `explanation` is shown once the player has confirmed that contradiction;
- a hint tier's text is shown only when the player explicitly requests that tier.

## 3. Keys and references

- Every item has a `key`: lowercase kebab-case, unique **within its type within the case** (e.g. `guest-photo`).
- Keys are **stable**. Once a case is published, never rename or delete a key (see ARCHITECTURE §8, D-14). Change text freely.
- References use these forms:

| Reference | Form | Example |
|---|---|---|
| Person | `<person>` | `corinne-blake` |
| Location | `<location>` | `east-room` |
| Evidence | `<evidence>` | `alarm-log` |
| Topic | `<person>/<topic>` | `corinne-blake/her-talk` |
| Statement | `<person>/<statement>` | `corinne-blake/at-lectern` |
| Contradiction | `<contradiction>` | `lectern-photo` |
| Generic discovered item | `<type>:<ref>` | `statement:corinne-blake/at-lectern` |

## 4. Unlock conditions (`requires`)

```yaml
requires:
  all:
    - examined: alarm-log
    - any:
        - asked: daniel-reyes/the-cameras
        - presented: daniel-reyes/camera-gap
```

| Atom | True when |
|---|---|
| `start` | Always (available at case start) |
| `visited: <location>` | Player has visited the location |
| `examined: <evidence>` | Player has opened the evidence detail |
| `asked: <person>/<topic>` | Player has asked that topic |
| `presented: <person>/<evidence>` | Player has shown that evidence to that person |
| `contradiction: <key>` | Player has correctly flagged that contradiction |
| `discovered: <type>:<ref>` | The referenced item is in the casefile |

Combinators: `all: [...]`, `any: [...]`, nestable, and each needs **at least one** condition (an empty list is an error). **No negation, no counters, no randomness.**

**Defaults when `requires` is omitted:**

| Item | Default |
|---|---|
| Person | `start` |
| Location | `start` |
| Evidence with a `location` | Discovered on `visited: <its location>` (an explicit `requires` is **added to** that implicit condition) |
| Evidence without a `location` | `start` (e.g. handed over in the briefing) |
| Topic | Available once its person is discovered (an explicit `requires` is **added to** that) |
| Statement | Revealed when its topic is asked or its reaction is triggered (statements don't take `requires`) |
| Timeline event | **Required**, and its source item must also be discovered (added implicitly, so an event never cites a hidden item) |

## 5. File specifications

Fields marked `*` are required, and unknown fields are rejected. Text fields accept a restricted Markdown subset (paragraphs, emphasis, lists, blockquotes). **Raw HTML is rejected by the validator.**

YAML tips: duplicate keys in a mapping are an error (plain YAML would silently keep the last one). Quote any value that contains a comma inside `{ … }` flow mappings, e.g. `{ key: overnight, label: "Overnight, after closing." }`.

### 5.1 `case.yaml`

```yaml
format_version: 1                       # * authoring format version
slug: the-missing-masterpiece           # * URL slug, unique, immutable once published
title: The Missing Masterpiece          # *
tagline: A priceless painting vanishes during a private preview.   # *
difficulty: standard                    # * introductory | standard | hard
estimated_minutes: 60                   # *
tags: [theft, art, locked-room]
content_notes: []                       # e.g. [death, alcohol] — shown on briefing (D-16)
setting:
  world_date: 2026-03-13                # * in-world date the main events happen
  era_note: Present day, London.
copyright: "© 2026 Avnish Ozarkar. All rights reserved."   # * shown in briefing footer and results (§7.1, D-20)
cover_image: assets/cover.webp          # *
cover_alt: The empty frame on the East Room wall.   # *
briefing: |                             # * player-visible introduction (Markdown)
  ...
objective: |                            # * what the player must determine
  ...
rating_thresholds:                      # optional; overrides global defaults
  airtight: 0.9
  convincing: 0.7
```

### 5.2 `people.yaml`

```yaml
- key: corinne-blake                    # *
  name: Corinne Blake                   # *
  role: Senior Curator                  # *
  is_suspect: true                      # * selectable as culprit
  portrait: assets/people/corinne-blake.webp
  portrait_alt: A woman in her fifties with silver-rimmed glasses.
  summary: Curated the preview exhibition and gave the evening's talk.   # * one line
  bio: |                                # player-visible background
    ...
  default_reaction: "I'm not sure what you want me to say about that."   # * used when shown evidence with no authored reaction
  requires: start                       # optional; default start
```

### 5.3 `locations.yaml`

```yaml
- key: east-room
  name: The East Room
  description: |
    ...
  image: assets/locations/east-room.webp
  image_alt: ...
  requires: start
```

### 5.4 `evidence.yaml`

```yaml
- key: alarm-log                        # *
  title: Alarm System Event Log         # *
  kind: record                          # * document | photo | object | record | correspondence | transcript
  location: security-office             # optional
  summary: A printout of yesterday's alarm events.   # * one line, shown in lists
  body: |                               # * full detail when examined
    ...
  image: assets/evidence/alarm-log.webp
  image_alt: ...                        # * required whenever image is set
  people: [daniel-reyes]                # persons this item concerns (for filtering)
  requires:                             # optional; added to implicit visited:<location>
    asked: daniel-reyes/the-system
```

For `record` and `transcript` kinds, `body` may use a fenced table or line-by-line format. The frontend renders these in the monospace "record" style (UI_UX_GUIDELINES §6).

### 5.5 `interviews.yaml`

```yaml
corinne-blake:                          # person key
  topics:
    - key: her-talk                     # *
      prompt: Ask about her talk in the Main Hall.   # * shown as the question
      requires: start                   # optional; default: when person discovered
      statements:                       # * one or more, revealed when asked
        - key: at-lectern
          text: "I was at the lectern from half past nine until ten. Ask anyone."
          claim:                        # optional: makes this statement a timeline claim
            from: "21:30"
            to: "22:00"
            location: main-hall
  reactions:                            # shown when the player presents the evidence
    - evidence: guest-photo             # *
      statements:
        - key: photo-reaction
          text: "Phones take odd pictures. I may have stepped aside for a moment."
```

A topic can be asked repeatedly. Its statements are revealed once and then re-displayed. To show a person changing their story, add a new topic gated by `requires` (typically on a contradiction). Don't change an existing topic's answer.

### 5.6 `timeline.yaml`

```yaml
- key: talk-scheduled
  title: Curator's talk (as scheduled)
  from: "21:30"                         # * HH:MM on world_date; "YYYY-MM-DDTHH:MM" for other days
  to: "22:00"                           # optional (point events omit)
  location: main-hall
  people: [corinne-blake]
  certainty: claimed                    # * claimed | verified
  source: { evidence: event-programme } # * exactly one of: evidence | statement
  requires: { examined: event-programme }  # *
```

Times are in-world wall-clock times with no timezone.

### 5.7 `accusation.yaml`

```yaml
intro: Present your case. This is final.   # shown above the form
questions:
  - key: culprit                        # *
    prompt: Who took the painting?      # *
    kind: person                        # * person | choice | evidence
    required_for_solve: true            # wrong answer ⇒ Unsolved
    cite: { min: 0, max: 0 }            # optional evidence slots for this question
  - key: method
    prompt: How was the painting removed without triggering the alarm?
    kind: choice
    options:                            # * for kind: choice
      - key: guard-disabled
        label: The security guard switched the alarm off.
      - key: override-bypass
        label: A maintenance override bypassed the East Room sensor.
      - key: forged-earlier
        label: The painting was swapped for a copy before the preview.
      - key: window-entry
        label: An outsider entered through the courtyard window.
    cite: { min: 1, max: 2, prompt: Cite the evidence that proves the method. }
```

- `kind: person` options are the case's discovered suspects.
- `kind: evidence` asks for citations only (e.g. "Where is the painting now? Cite the item that proves it.").
- Citable items: evidence, statements, and found contradictions.
- Option labels **must not** reveal which one is correct by wording, length, or specificity. Write distractors with equal care.

### 5.8 `spoilers/contradictions.yaml`

```yaml
- key: lectern-photo
  statement: corinne-blake/at-lectern   # *
  conflicts_with:                       # * exactly one of:
    evidence: guest-photo               #     evidence: <key>
                                        #     statement: <person>/<statement>
  explanation: |                        # * shown once found
    The guest's photo, time-stamped 21:51, shows the lectern empty during
    the period Corinne claims she was speaking.
  accept_also:                          # optional alternative pairings that also count
    - { evidence: talk-recording }
```

### 5.9 `spoilers/solution.yaml`

```yaml
answers:                                # * one entry per accusation question
  culprit:
    correct: corinne-blake
    points: 30
    explanation: ...
  method:
    correct: override-bypass
    points: 10
    proof:                              # scoring for cited items
      points: 10
      full:    [[alarm-log], [alarm-test-email, camera-gap]]   # any one full set ⇒ full proof points
      partial: [[camera-gap]]                                  # ⇒ half proof points
    explanation: ...
summary: One-paragraph "what really happened".            # *
narrative: |                                              # * full reveal, shown on results
  ...
red_herrings:                                             # * one entry per non-culprit suspect
  - person: vivian-ashcombe
    suspicion: Recently increased the insurance cover.
    cleared_by: [lender-letter]                           # * discoverable items that clear them
    explanation: ...
key_evidence: [guest-photo, alarm-log, courier-booking, dismissal-draft, return-crate, cotton-gloves]   # * drives "evidence you missed"
answer_terms: ["took the painting", "in the crate", "dismissal"]   # giveaway phrases hints must not contain (F14)
walkthrough:                                              # * a minimal winning action sequence (used by automated tests)
  - visit: main-hall
  - examine: event-programme
  - ask: corinne-blake/her-talk
  # ...
  - accuse:
      culprit: { answer: corinne-blake }
      method: { answer: override-bypass, cite: [alarm-log] }
```

**Walkthrough steps** (one action per step; it must end with exactly one `accuse`):

| Step | Meaning |
|---|---|
| `visit: <location>` | visit a discovered location |
| `examine: <evidence>` | open a discovered evidence item |
| `ask: <person>/<topic>` | ask an available topic |
| `present: <person>/<evidence>` | show evidence to a person |
| `flag: { statement: <p>/<s>, evidence: <e> }` or `flag: { statement: <p>/<s>, other_statement: <p>/<s> }` | flag a pairing; it must match an authored contradiction |
| `accuse: { <question>: { answer: <key>, cite: [...] }, ... }` | cited items must be discovered; the result must be Solved · Airtight |

**Citation shorthand** (in `proof`, `cleared_by`, `mentions`, walkthrough `cite`): a bare key is evidence (`alarm-log`). Other types use a prefix: `statement:corinne-blake/at-lectern`, `contradiction:lectern-photo`. The importer normalises all of these to the typed reference format in DATA_MODEL §6.

Scoring per question = answer points (if correct) + proof points (if a `full` set is contained in the citations; half, rounded down, if only a `partial` set is). Proof points are awarded **only if the answer is correct**. Score % = earned / maximum. Outcome tiers are in PRODUCT_SPEC §6. Hint use doesn't affect the score unless D-21 decides otherwise.

### 5.10 `spoilers/hints.yaml` (D-04)

```yaml
- key: test-curator-alibi               # *
  goal: Test the curator's account of the evening.   # * player-facing label, shown once the track is offered
  priority: 10                          # lower = offered first when several tracks are relevant
  requires:                             # * when the track becomes relevant (same condition language as §4)
    all:
      - asked: corinne-blake/her-talk
      - visited: main-hall
      - asked: sam-pike/guests-phones   # guarantees guest-photo is discovered, so tier 3 may name it
  resolved_when:                        # * when the track stops being offered (goal achieved)
    contradiction: lectern-photo
  mentions: [statement:corinne-blake/at-lectern, guest-photo]   # * every item any tier names (citation shorthand)
  tiers:                                # * exactly 3, in order
    - level: nudge                      # where to focus
      text: Corinne was confident about where she was all evening. Is anyone else's view of the Main Hall worth checking?
    - level: pointer                    # which items to consider together
      text: Guests were taking photos all evening. Look at what was captured in the Main Hall next to Corinne's account of her talk.
    - level: direction                  # the exact comparison/action — still no conclusion
      text: Compare Corinne's statement about being at the lectern until ten with the time-stamped guest photo from the Main Hall.
```

Rules:
- A track is **offered** when `requires` is satisfied and `resolved_when` isn't. Among offered tracks, the player gets the lowest `priority` first, and can switch tracks.
- Tiers are revealed strictly in order: nudge → pointer → direction. Earlier tiers stay visible.
- **`mentions` must list every item named in any tier**, and each mentioned item must be guaranteed discovered whenever the track is offered (validator rule F12). A hint may *point toward* an undiscovered item only by describing an action ("ask the valet about photos"), never by naming the item.
- The **direction** tier names a specific comparison or action. It must **never** state the conclusion: no "X is lying", "X did it", motive, method, or location of the stolen item.

## 6. Writing standards

### 6.1 Structure targets

| | Introductory | Standard | Hard |
|---|---|---|---|
| Suspects | 3 | 4–5 | 5–6 |
| Locations | 3–4 | 4–6 | 6–8 |
| Evidence items | 12–18 | 20–30 | 30–45 |
| Authored contradictions | 2 | 3–4 | 4–6 |
| Contradictions required to reach key evidence | 1 | 1–2 | 2–3 (layered) |
| Hint tracks | 4–6 | 6–10 | 8–14 |
| Estimated time | 20–35 min | 45–75 min | 75–120 min |

### 6.2 Story

- **One true account.** Write the full hidden narrative (what actually happened, minute by minute) *before* writing any evidence. Every piece of evidence must be consistent with it.
- **The crime must be explained by means, motive, and opportunity**, each supported by evidence.
- **The culprit appears early.** The culprit must be discoverable at start or within the first location visited.
- **Everyone has a secret.** Non-culprit suspects should have something to hide, so that lying isn't proof of guilt.

### 6.3 Suspects, motives, alibis

- Each suspect has: a plausible motive, a stated alibi, and either evidence that breaks the alibi or evidence that confirms it.
- At least one non-culprit should have an alibi that *looks* weak but holds up.
- Statements are written in the character's voice and stay internally consistent unless the inconsistency is an authored contradiction.

### 6.4 Evidence

- Each item has one primary purpose: establish a fact, place someone, break an alibi, show motive, clear a suspect, or add texture. Pure-texture items: ≤ 20% of evidence.
- Summaries must not give away an item's significance ("A printout of alarm events", not "Proof the alarm was bypassed").
- Image-only clues must also be expressed in `body` or `image_alt` so the case stays solvable without sight (accessibility).
- Times, names, and numbers must match exactly across items. The validator cross-checks timeline claims.

### 6.5 Contradictions

- Must be **decisive**: once a player sees both sides, a reasonable person agrees they can't both be true.
- Must be **discoverable**: both sides reachable without already having found the contradiction.
- Where a different but equally valid pairing exists, add it to `accept_also` so a correct player isn't told "doesn't hold up".
- Should **pay off**: most contradictions unlock something (a confrontation topic, a location, evidence).

### 6.6 Hints

- **Cover every step that the solution depends on.** Every contradiction and `key_evidence` item used in a `full` proof set should resolve at least one track (validator rule F13).
- **Teach the method, not the answer.** Good hints teach the player to compare a claim against a record, or to check who could have seen something. They never name a suspect as guilty.
- **Escalate gently.** Nudge = where to look. Pointer = which two things belong together. Direction = the exact comparison. There's no fourth tier, so the player still makes the final deduction.
- **Stay in voice.** Hints are written as the detective's inner notes, in calm second person, matching UI copy (UI_UX_GUIDELINES §10).
- **Never mislead.** Hints don't point at red herrings, even to "balance" difficulty.

### 6.7 Fairness rules (enforced by validator ✓ or reviewer ✎)

| # | Rule | Check |
|---|---|---|
| F1 | Every accusation question's correct answer is reachable, with at least one `full` proof set entirely discoverable | ✓ |
| F2 | Every `key_evidence` item and every red herring's `cleared_by` item is discoverable | ✓ |
| F3 | No content is orphaned (unreachable under any play) | ✓ (warning) |
| F4 | The culprit is discoverable at start or after ≤ 1 visit | ✓ |
| F5 | Every non-culprit suspect has a red-herring entry with `cleared_by` | ✓ |
| F6 | The `walkthrough` executes and produces an Airtight result | ✓ |
| F7 | Every image with clue value has equivalent text | ✎ |
| F8 | No solution depends on outside knowledge beyond common sense (no specialist chemistry, no real-world trivia) | ✎ |
| F9 | Distractor accusation options are equally plausible in wording | ✎ |
| F10 | The narrative cites only player-discoverable items | ✎ |
| F11 | The case has been playtested by at least one person who didn't write it, and they found it fair | ✎ |
| F12 | Every hint track has exactly 3 tiers; its `requires` is reachable before `resolved_when`; every `mentions` item is guaranteed discovered whenever the track is offered | ✓ |
| F13 | Every contradiction and `key_evidence` item used in a `full` proof set is in some track's `resolved_when` (coverage) | ✓ (warning) |
| F14 | No hint text contains a correct accusation option label or any phrase in `solution.yaml` → `answer_terms` (author-listed giveaway phrases, e.g. "took the painting", "the crate") (lint). Naming a person whose *statement* should be checked is allowed | ✓ (warning) |
| F15 | No hint states a conclusion (guilt, motive, method, location); hints don't point at red herrings | ✎ |

## 7. Assets

- Format: WebP (JPEG fallback not needed). Max 1600 px on the long edge for evidence and locations, 800 px for portraits.
- Every image requires alt text, written to describe what a careful observer would notice.
- Use original, licensed, or public-domain imagery only. Record the source **and license** of every third-party asset in `assets/CREDITS.md`. Assets with a license that forbids public redistribution can't be committed (the repository is public, D-19).

### 7.1 Copyright of case content (D-20)

- Application code is MIT-licensed (`LICENSE`, added in M0.1). **Case content isn't.** Original narratives, characters, dialogue, evidence text, hints, solutions, and original artwork under `content/cases/` are © the author, all rights reserved, as stated in `content/COPYRIGHT.md`. That changes only if the owner explicitly licenses specific content for reuse.
- Every case folder carries a short `COPYRIGHT` line in `case.yaml` (`copyright: "© 2026 <author>. All rights reserved."`), shown in the briefing footer and the results page.
- Third-party assets keep their own licenses, as recorded in `CREDITS.md`.
- The fixture case (`_fixtures/mini-case`) and `_template` are test scaffolding and are MIT-licensed with the code.

### 7.2 Public-repository spoiler notice (D-25)

The repository is public, so `spoilers/` files are readable by anyone who browses it. Until D-25 is revisited, `content/README.md` and the root README carry a prominent spoiler warning.
- Filenames are replaced with content hashes on import, so URLs don't reveal keys (ARCHITECTURE §7).

## 8. Validation & publication workflow

1. **Schema check**: every file is parsed and validated against the format version.
2. **Reference check**: every key reference resolves; keys are unique per type.
3. **Graph check**: build the unlock graph and run every possible action until nothing new appears:
   - repeatedly visit every discovered location, examine every discovered evidence item, ask every available topic, present every discovered evidence item to every discovered person, and flag every authored contradiction whose two sides are discovered;
   - stop when nothing new is discovered (guaranteed, because conditions are monotonic and finite).
4. **Fairness check**: rules F1–F6 and F12–F14 run against the final reachable set.
5. **Walkthrough check**: the `walkthrough` is replayed through the real discovery engine and scoring service.
6. **Report**: errors block import. Warnings (e.g. F3 orphans) are listed. The validator can optionally output the unlock graph as Mermaid text.

```bash
backend/.venv/bin/python backend/manage.py validate_case content/cases/<slug>            # one case
backend/.venv/bin/python backend/manage.py validate_case --all                           # every case not starting with "_"
backend/.venv/bin/python backend/manage.py validate_case content/cases/<slug> --mermaid  # also print the unlock graph
backend/.venv/bin/python backend/manage.py validate_case --all --strict                  # warnings fail too
```

How the hint checks (F12) work:
- **Offered before resolved:** the validator looks for a reachable state where `resolved_when` is still false and `requires` is true.
- **Mentions are safe:** for every minimal way to satisfy `requires` (its disjunctive normal form), it discovers only what those facts imply. Each mentioned item must be found in every case. Flagging a contradiction counts as having found both its sides, and examining or asking counts as having found the item or topic.
- **Coverage (F13):** an item counts as covered when it appears in a track's `mentions` or `resolved_when`.
7. **Import** as draft → staff playtest in preview mode → **publish**.

## 9. Example case: *The Missing Masterpiece* (player-visible content)

> This section shows only what a player could eventually see. It is abridged: a production version would have ~24 evidence items and fuller text.

**Briefing.** On the evening of Friday 13 March, the Ashcombe Gallery held a private preview of its spring exhibition. At 22:15, a guest noticed that *The Cartographer's Daughter* (1891, Aurélie Marchand), the gallery's most valuable work, insured for £2.4 million, was gone from the locked East Room. The alarm never sounded. No one has left the building's grounds with anything large enough to hold the canvas. You have the morning before the insurer's investigators arrive.

**Objective.** Determine who took the painting, how they removed it without triggering the alarm, why they did it, and where it is now.

**People**

| Key | Name | Role | Suspect |
|---|---|---|---|
| `vivian-ashcombe` | Vivian Ashcombe | Gallery owner | ✓ |
| `daniel-reyes` | Daniel Reyes | Head of security | ✓ |
| `corinne-blake` | Corinne Blake | Senior curator | ✓ |
| `felix-okafor` | Felix Okafor | Freelance restorer, guest | ✓ |
| `harriet-lowe` | Harriet Lowe | Private collector, guest | ✓ |
| `sam-pike` | Sam Pike | Valet attendant | witness |

**Locations:** `east-room`, `main-hall`, `security-office`, `curators-office`, `loading-bay`, `courtyard`.

**Selected evidence (player-visible text)**

| Key | Kind | Location | Summary |
|---|---|---|---|
| `event-programme` | document | main-hall | The printed programme for the preview evening. |
| `guest-photo` | photo | main-hall (requires `asked: sam-pike/guests-phones`) | A guest's phone photo of the Main Hall, with metadata. |
| `alarm-log` | record | security-office | A printout of the day's alarm system events. |
| `camera-gap` | record | security-office | CCTV recording index for the evening. |
| `alarm-test-email` | correspondence | curators-office | An email thread about the alarm system. |
| `courier-booking` | correspondence | curators-office | A courier confirmation email. |
| `dismissal-draft` | document | requires `contradiction: lectern-photo` | A letter found in the owner's desk tray. |
| `insurance-rider` | document | security-office | An amendment to the gallery's insurance policy. |
| `lender-letter` | correspondence | requires `presented: vivian-ashcombe/insurance-rider` | A letter from the gallery's bank. |
| `valet-log` | record | courtyard | The valet's handwritten log for the evening. |
| `return-crate` | object | loading-bay (requires `examined: courier-booking`) | A wooden shipping crate awaiting collection. |
| `cotton-gloves` | object | curators-office (requires `contradiction: override-user`) | A pair of white cotton handling gloves. |

**Excerpt of `alarm-log` body (record style):**
```
15:10  MAINT OVERRIDE ENABLED       user: CBLAKE
15:12  SYSTEM TEST STARTED
15:40  SYSTEM TEST COMPLETE
21:47  ZONE 4 (EAST RM) SENSOR      BYPASS ACTIVE
21:48  CCTV RECORDER RESTART
22:04  CCTV RECORDER ONLINE
22:03  ZONE 4 (EAST RM) SENSOR      BYPASS CLEARED
```

**Accusation questions**

| Key | Prompt | Kind | Cite |
|---|---|---|---|
| `culprit` | Who took the painting? | person (required) | none |
| `opportunity` | When did the culprit have the chance? | choice: during the 21:45 intermission / before the guests arrived / after the alarm was discovered / overnight | 1–2 |
| `method` | How was it removed without the alarm? | choice (see §5.7) | 1–2 |
| `motive` | Why? | choice: insurance payout / impending dismissal and a private buyer / gambling debts / revenge on a rival / to protect the painting from sale | 1–2 |
| `location-now` | Where is the painting? | evidence | 1 |

---

## 10. Spoiler section: *The Missing Masterpiece* solution

> ⛔ **SPOILERS BELOW.** This content lives in `spoilers/` and is shown to players only on the results screen.

**What happened.** Corinne Blake learned from a draft letter that Vivian Ashcombe meant to dismiss her and sell the Marchand at auction. A private buyer had approached Corinne months earlier. At 15:10 she logged a maintenance override, under the pretext of an alarm test she had requested by email "to calibrate for the preview". The override let her schedule a sensor bypass for Zone 4. At 16:02 she booked a courier from her workstation to collect "one crate, Okafor Studio – return" at 14:00 the next day, after the morning the player has to investigate. Her talk was printed as 21:30–22:00, but she ended it at 21:45 with an "intermission" slide. Between 21:47 and 22:03 she removed the canvas from its frame while wearing handling gloves and packed it into the restorer's return crate in the loading bay. The bypass caused the CCTV recorder to restart (offline 21:48–22:04), which covered her whole time in the East Room and the loading bay.

**Answer key**

| Question | Correct | Answer pts | Proof pts | Full proof sets |
|---|---|---|---|---|
| culprit | `corinne-blake` | 30 | — | — |
| opportunity | `during-intermission` (during the 21:45 intermission) | 10 | 5 | `[guest-photo]` · `[contradiction:lectern-photo]` |
| method | `override-bypass` | 10 | 10 | `[alarm-log]` · `[alarm-test-email, camera-gap]` |
| motive | `dismissal-and-buyer` (impending dismissal and a private buyer) | 10 | 10 | `[dismissal-draft]` (partial: `[statement:corinne-blake/buyer-admission]`) |
| location-now | — (evidence) | — | 15 | `[return-crate]` · `[courier-booking]` |
| **Total** | | **60** | **40** | **= 100** |

**Contradictions**

| Key | Statement | Conflicts with | Unlocks |
|---|---|---|---|
| `lectern-photo` | `corinne-blake/at-lectern` ("at the lectern until ten") | `guest-photo` (lectern empty at 21:51) | `dismissal-draft`; topic `corinne-blake/the-intermission` |
| `override-user` | `corinne-blake/never-touch-system` ("I never touch the security system") | `alarm-log` (override by CBLAKE) | `cotton-gloves`; topic `corinne-blake/the-buyer` |
| `monitor-room` | `daniel-reyes/watched-monitors` ("I never left the monitors") | `valet-log` (Daniel in the courtyard 21:44–21:56) | topic `daniel-reyes/the-smoke-break` (clears Daniel of collusion, explains the unseen camera gap) |
| `no-booking` | `felix-okafor/no-pickup-booked` ("I never arranged a pickup") | `courier-booking`: **not a contradiction**. The booking came from the curator's workstation, which supports Felix. It is a tempting pairing that won't confirm. Flagging it costs nothing (D-03); it just stays unconfirmed. | — |

**Red herrings**

| Suspect | Why suspicious | Cleared by |
|---|---|---|
| Vivian Ashcombe | Raised the insurance cover two weeks ago | `lender-letter`: the bank required the increase as a loan condition |
| Daniel Reyes | Controls the alarm; cameras went down; lied about his whereabouts | `alarm-log` (override user is CBLAKE) + `monitor-room` contradiction (his lie hides a smoke break, not the theft) |
| Felix Okafor | The crate is addressed to his studio | `courier-booking` sent from the curator's workstation; `valet-log` places him in the courtyard 21:40–22:05 |
| Harriet Lowe | Publicly said the painting "should have been mine" | `valet-log` (with Felix in the courtyard); her car never moved |

**Why it's fair:** opportunity, means, and motive each have at least one independent proof path. The culprit is discoverable at start. Every suspect has a secret. The one "obvious" lie (Daniel's) belongs to someone who isn't the culprit.

**Hint tracks (abridged)**

| Track | Offered when | Resolved when |
|---|---|---|
| `test-curator-alibi` | asked `corinne-blake/her-talk` + visited `main-hall` + asked `sam-pike/guests-phones` | `contradiction: lectern-photo` |
| `who-touched-the-system` | examined `alarm-log` | `contradiction: override-user` |
| `where-did-it-go` | examined `alarm-test-email` or `camera-gap` | examined `return-crate` |
| `why-now` | `contradiction: lectern-photo` | examined `dismissal-draft` |
| `the-guards-story` | asked `daniel-reyes/the-cameras` | `contradiction: monitor-room` |
| `the-insurance-question` | examined `insurance-rider` | examined `lender-letter` |

The last two tracks help the player *clear* suspects. Their hints point toward the clearing evidence, not toward suspicion.
