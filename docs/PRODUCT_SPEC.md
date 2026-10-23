# Casefile: Product Specification

**Status:** Planning draft. Nothing here is implemented.
**Related:** [SCREEN_DESIGN](SCREEN_DESIGN.md) · [CASE_DESIGN](CASE_DESIGN.md) · [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md)

This document describes the **complete intended product**. The order of building it is in the roadmap. Features are tagged:

- **[Essential]**: required for the v1.0 release.
- **[Optional]**: valuable enhancement, planned after v1.0 or if time allows. The architecture must not block these.

Open product questions are listed in [§9 Open decisions](#9-open-decisions) with IDs (`D-01`…). Other documents refer to those IDs instead of repeating or inventing answers. Where a document needs a working assumption, it is labelled **"Default pending D-xx"**.

---

## 1. Product summary

Casefile is a web-based detective game in which the player investigates hand-authored mysteries. They gather evidence, interview suspects, expose contradictions, rebuild the timeline, develop theories, and finally submit an accusation that has to be justified with evidence. The player wins by reasoning correctly, not by guessing a name.

## 2. Target audience

| Segment | Description | What they need |
|---|---|---|
| **Primary: armchair detectives** | Adults who enjoy mystery novels, true-crime podcasts, escape rooms, *Return of the Obra Dinn*, *Her Story*, *Ace Attorney*, boxed "murder mystery file" games | Fair puzzles, satisfying "aha" moments, real deduction |
| **Secondary: casual puzzle players** | People who play daily puzzles (crosswords, Wordle-likes) | Clear onboarding, sessions that can be paused and resumed, no punishing failure |
| **Tertiary: groups and couples** | People investigating together around one screen | A readable layout on a laptop or TV, shareable notes |

Assumptions to validate:
- Players are 16+ (see D-16 for content tone).
- A case takes 20–120 minutes in total, depending on difficulty (CASE_DESIGN §6.1), and is often split across several sittings.
- Desktop and tablet are the primary devices. Phones support full play, with list-based board and timeline views instead of canvases (default pending D-13).

## 3. What makes Casefile distinctive

1. **Accusations need reasons.** The player names the culprit *and* the method and motive, and attaches the evidence that proves each claim. A correct name with no proof earns a lower rating than a fully argued case.
2. **Contradictions are the core mechanic.** Progress comes from the player noticing that a statement conflicts with evidence and formally flagging it. The game never highlights contradictions for the player.
3. **Every case is provably fair.** Each case passes an automated solvability check before publication: every fact needed for the solution can be discovered through play. Every red herring can be eliminated with discoverable evidence.
4. **Nothing is graded mid-investigation.** Theories, board links, and notes are the player's own thinking space. The game does not say whether a theory is right until the accusation.
5. **Cases are content.** One engine runs many mysteries of different shapes (theft, disappearance, murder, fraud) through a small, fixed set of mechanics configured by data.
6. **Atmosphere without friction.** The case-file aesthetic (paper, typewritten records, photographs, a corkboard) sits on top of a clean, accessible, keyboard-friendly interface.

## 4. Core gameplay loop

```
            ┌──────────────────────────────────────────────┐
            │                                              │
 Briefing ──► Explore ──► Examine ──► Question ──► Compare ─┤
              (locations)  (evidence)  (suspects)  (statements vs.
                                                    evidence/timeline)
                                                       │
                                     Flag contradiction ─► New leads unlock
                                                       │
                              Organise: board · timeline · notes · theories
                                                       │
                                                       ▼
                                   Accuse (who · how · why + proof)
                                                       │
                                                       ▼
                                 Results · full solution · missed evidence
```

1. **Briefing**: the player learns what happened, what they're asked to determine, and who the initial persons of interest are.
2. **Explore**: visiting a location reveals the evidence that can be found there.
3. **Examine**: opening an evidence item shows its full detail. Examining can unlock further evidence, topics, or locations.
4. **Question**: the player asks a person about an available topic, or presents a piece of evidence to them. Answers are recorded as **statements** in the casefile.
5. **Compare**: the player reviews statements against evidence and the timeline. When they find a conflict, they **flag a contradiction** by pairing a statement with the evidence (or another statement) it conflicts with.
   - A correct flag is recorded and typically unlocks new topics, evidence, or locations.
   - An incorrect flag gives neutral feedback ("That doesn't hold up") and reveals nothing (penalty: D-03).
6. **Organise**: the player pins items to the evidence board, links them, writes notes, and drafts theories.
7. **Accuse**: once confident, the player answers the case's accusation questions and attaches supporting evidence, then confirms.
8. **Resolve**: the player sees the outcome, rating, score breakdown, full solution, red-herring explanations, and the key evidence they missed.

All progress saves on the server after every action. The player can leave and resume at any time.

## 5. Feature set

### 5.1 Accounts and access
| Feature | Tag | Notes |
|---|---|---|
| Register / log in / log out (email + password) | Essential | Session-cookie auth; see ARCHITECTURE |
| Server-side saved progress for logged-in players | Essential | |
| Password reset via email | Essential | Email provider: D-17 |
| Guest play (try a case without an account) | **Decision D-01** | Default pending D-01: account required |
| Profile: display name, preferences (text size, reduced motion, theme) | Essential | |
| Account deletion and data export | Essential | Basic privacy hygiene |
| Social login (Google/Apple) | Optional | |

### 5.2 Case library and briefing
| Feature | Tag |
|---|---|
| Library of published cases with cover, title, tagline, difficulty, estimated length, tags | Essential |
| Per-case player status: not started / in progress / solved (with rating) / unsolved | Essential |
| Filter by status, difficulty, and tag; sort by newest or difficulty | Essential |
| Case briefing screen: synopsis, objective, starting persons of interest, content notes | Essential |
| Start new investigation / resume / replay (new playthrough) | Essential |
| "Coming soon" teaser cases | Optional |
| Case series / seasons with a recurring detective storyline | Optional |

### 5.3 Investigation workspace
| Feature | Tag |
|---|---|
| Workspace shell with persistent navigation between Overview, Locations, Evidence, People, Timeline, Board, Theories, Accuse | Essential |
| **Locations**: visit to reveal evidence; location description and image | Essential |
| **Evidence**: list with filters (type, location, person, unread); detail view with full text and image zoom | Essential |
| Evidence kinds: document, photograph, physical object, record/log, correspondence, audio transcript | Essential (rendered by type; no audio playback needed) |
| "New" badges for items discovered since last viewed | Essential |
| **Case notebook**: free-text notes, optionally attached to any item | Essential |
| Search across all discovered content | Essential |
| Discovery feed: chronological log of what the player found and how | Essential |
| Audio evidence with playback (with transcript) | Optional |
| Image hotspots (click regions of a scene photo to discover evidence) | Optional |

### 5.4 People and interviews
| Feature | Tag |
|---|---|
| People directory: suspects and witnesses with portrait, role, relationship to case | Essential |
| Suspect profile: bio, known facts, recorded statements, linked evidence, player notes | Essential |
| **Ask about topic**: topics become available through discovery | Essential |
| **Present evidence**: show any discovered evidence; authored reactions for relevant items, a generic per-person response otherwise | Essential |
| Statements recorded verbatim and quotable (citable in contradictions, theories, accusation) | Essential |
| Player-assigned suspicion marker per person (private, ungraded) | Essential |
| Pressure / composure mechanic that affects answers | Optional |
| Free-text questioning powered by an LLM | **Decision D-11**; out of scope for v1.0 by default |

### 5.5 Contradictions
| Feature | Tag |
|---|---|
| Flag contradiction: select a statement + a conflicting evidence item or statement | Essential |
| Server verifies against authored contradictions; correct flags unlock content | Essential |
| Neutral feedback for incorrect flags that leaks nothing | Essential |
| Found-contradictions list with authored explanation | Essential |
| Penalty or limit for incorrect flags | **Decision D-03** |

### 5.6 Timeline
| Feature | Tag |
|---|---|
| Timeline of discovered events, lanes per person (and filter by location) | Essential |
| Each event marked **claimed** (from a statement) or **verified** (from evidence) with its source | Essential |
| Overlapping placements visually apparent (same person, two places) but **not** auto-flagged | Essential |
| Jump from an event to its source statement/evidence | Essential |
| Player-added custom timeline markers | Optional |

### 5.7 Evidence board
| Feature | Tag |
|---|---|
| Pin any discovered item (evidence, person, statement, timeline event, contradiction, note) as a card | Essential |
| Free arrangement by drag; **keyboard-accessible** move and link alternatives | Essential |
| Labelled links between cards ("contradicts", "places at scene", custom text) | Essential |
| Auto-save layout | Essential |
| Group/cluster frames, colour tags | Optional |
| Export board as image | Optional |

### 5.8 Theories
| Feature | Tag |
|---|---|
| Create multiple named theories: suspect, method, motive, opportunity, supporting items, open questions | Essential |
| Mark a theory active / discarded | Essential |
| Compare two theories side by side | Optional |
| Prefill the accusation from a theory | Essential |
| Theories are **never graded** before accusation | Essential (principle) |

### 5.9 Accusation and results
| Feature | Tag |
|---|---|
| Accusation form defined per case: ordered questions (suspect choice, multiple choice, evidence citation) | Essential |
| Evidence slots per claim (e.g. "Prove opportunity: cite up to 2 items") | Essential |
| Review step and explicit "final" confirmation | Essential |
| Number of accusation attempts | **Decision D-02**; default pending: one attempt per playthrough |
| Outcome: **Solved** or **Unsolved**, plus rating tier (see §6) | Essential |
| Score breakdown per question with the correct answer and explanation | Essential |
| Full solution narrative ("How it happened") | Essential |
| Red herrings explained | Essential |
| "Evidence you missed": key items not discovered | Essential |
| Playthrough statistics: time spent, % evidence found, contradictions found, incorrect flags | Essential |
| Replay case (new playthrough) | Essential |
| Shareable spoiler-free result card | Optional (D-09) |

### 5.10 Player progress
| Feature | Tag |
|---|---|
| Progress page: cases solved, ratings, in-progress investigations, totals | Essential |
| Playthrough history per case | Essential |
| Detective rank based on cumulative performance | Optional |
| Achievements (e.g. "No wrong flags", "Found every clue") | Optional |
| Leaderboards | Optional (D-09) |

### 5.11 Hints
| Feature | Tag |
|---|---|
| Tiered, authored hints per case stage ("nudge" → "pointer" → "explicit") | **Decision D-04**; Optional by default |
| Hint usage reflected in rating | Depends on D-04 |

### 5.12 Content pipeline (author-facing)
| Feature | Tag |
|---|---|
| YAML case format with separate spoiler file | Essential |
| `validate_case` command: schema, references, unlock graph, solvability, fairness rules | Essential |
| `import_case` command: idempotent import/update, publish/unpublish | Essential |
| Django admin read-only views for inspecting content and playthroughs | Essential |
| Case preview mode for staff (play drafts, reveal-all toggle) | Essential |
| Unlock-graph visualisation output from the validator (e.g. Mermaid/Graphviz text) | Optional |
| In-browser authoring tool | Optional (D-10) |

### 5.13 Presentation
| Feature | Tag |
|---|---|
| Dark "case file" theme | Essential |
| Light "daylight" theme | **Decision D-08**; Optional by default |
| Reduced-motion mode, adjustable text size | Essential |
| Ambient audio / sound effects | Optional (D-12) |
| Localisation | Optional; strings externalised from the start |

### 5.14 Launch content
- v1.0 ships with **multiple cases**. Default pending D-05: **three**, of varied shape and difficulty:
  1. *The Missing Masterpiece*: art theft, Standard difficulty (worked example in CASE_DESIGN).
  2. A second case with a different crime type (e.g. a disappearance or poisoning), Introductory difficulty, doubling as the tutorial case (D-18).
  3. A third case, Hard difficulty, with more suspects and two layered contradictions.
- Cases 2 and 3 are outlined during the roadmap's content milestones. They are not designed in this planning phase.

## 6. Scoring and ratings (working definition)

Each case's accusation questions carry points (defined in the case's `accusation.yaml` and `solution.yaml`). Outcome:

| Outcome | Condition |
|---|---|
| **Solved: Airtight** | All `required_for_solve` questions correct **and** score ≥ 90% |
| **Solved: Convincing** | All required questions correct **and** score ≥ 70% |
| **Solved: Shaky** | All required questions correct, score < 70% (right answer, weak proof) |
| **Unsolved** | Any required question wrong (typically: wrong culprit) |

Thresholds are global defaults that a case may override. Whether hints (D-04), incorrect flags (D-03), or elapsed time (D-15) adjust the score is still open. Until decided, **they do not affect score**; they only appear as statistics.

## 7. User-experience principles

1. **The player is the detective.** The UI shows what has been found and never what it means.
2. **No dead ends.** Unlock rules are monotonic: the player can never lose access to content or make a case unwinnable. The validator enforces this.
3. **No leaks.** Undiscovered content, including counts that hint at it (e.g. "3 of 12 evidence"), is never sent to the client before accusation. Exception: a case may opt in to showing a total evidence count after results.
4. **Every claim is traceable.** Every statement, event, and contradiction links back to its source.
5. **Respect the player's time.** Progress auto-saves, any screen is reachable in at most 2 clicks within the workspace, and the briefing can be revisited.
6. **Atmosphere serves legibility.** Documents are rendered readably first and stylised second. Decorative fonts never appear on long text.
7. **Accessible by default.** WCAG 2.2 AA. Every drag interaction has a keyboard alternative.
8. **Failure is still an ending.** An unsolved case still reveals the full solution and missed evidence, so the player learns.

## 8. Non-goals (for v1.0)

- Real-time multiplayer or co-op sessions.
- Procedurally generated mysteries.
- User-generated cases published by players.
- Native mobile apps.
- Payments or subscriptions (D-06).

## 9. Open decisions

These need the product owner's input. Until a decision is made, the listed default is used for planning only.

| ID | Question | Planning default | Affects |
|---|---|---|---|
| **D-01** | Allow guest play without an account? If so, are guest playthroughs migrated on sign-up? | Account required to start a case; library & briefings public | Auth, API permissions, data model (nullable user) |
| **D-02** | How many accusation attempts per playthrough? Multiple attempts with a score penalty? | One attempt; replay starts a new playthrough | Accusation API, scoring, results UI |
| **D-03** | Penalise incorrect contradiction flags (score penalty, limited attempts, or none)? | No penalty; counted as a statistic | Scoring, contradiction UI copy |
| **D-04** | Include a hint system in v1.0? Does hint use lower the rating? | Not in v1.0; data model reserves space | Content format, scoring, roadmap |
| **D-05** | How many cases at launch? | Three | Roadmap length, content effort |
| **D-06** | Business model: free, one-time purchase, case packs, subscription? | Free, no payments in v1.0 | Out of scope until decided |
| **D-07** | Hosting/deployment target (e.g. Render, Fly.io, Railway, a VPS, AWS)? | Single container + managed PostgreSQL on a PaaS | Deployment milestone |
| **D-08** | Ship a light theme in v1.0? | Dark theme only in v1.0; tokens support a second theme | UI guidelines |
| **D-09** | Public leaderboards or shareable result cards? | Neither in v1.0 | Privacy, API |
| **D-10** | Who authors cases long-term: only the core team via YAML, or invited authors via an in-app editor? | Core team via YAML | Content pipeline, roadmap post-1.0 |
| **D-11** | Use an LLM for free-form interviews in future? | No; authored topics only | Architecture extension point only |
| **D-12** | Ambient audio and sound effects? | Not in v1.0 | UI guidelines, assets |
| **D-13** | Phone support level: full play, or reading/light play with a simplified board? | Full play on ≥ 768px; phones get list-based board and timeline | Screen design, testing matrix |
| **D-14** | When a published case is updated, what happens to in-progress playthroughs? | Additive changes apply live; breaking changes are blocked while playthroughs are in progress (see ARCHITECTURE §8) | Importer, data model |
| **D-15** | Should elapsed time or number of actions affect score? | No; shown as statistics only | Scoring |
| **D-16** | Content tone and age rating: are murders and violence allowed, and how graphic? | Non-graphic; violence off-screen; content notes on briefing | Case design standards |
| **D-17** | Transactional email provider (password reset, verification)? Require email verification? | Provider TBD; verification optional in v1.0 | Auth milestone |
| **D-18** | Is there a dedicated interactive tutorial, or does the Introductory case teach through contextual tips? | Introductory case plus dismissible contextual tips | Screen design, case 2 design |
