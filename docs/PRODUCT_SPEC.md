# Casefile: Product Specification

**Status:** Planning draft. Nothing here is implemented.
**Related:** [SCREEN_DESIGN](SCREEN_DESIGN.md) · [CASE_DESIGN](CASE_DESIGN.md) · [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md)

This document describes the **complete intended product**. The order of building it is in the roadmap. Features are tagged:

- **[Essential]**: required for the v1.0 release.
- **[Optional]**: valuable enhancement, planned after v1.0 or if time allows. The architecture must not block these.

Product decisions, both decided and open, are listed in [§9 Decisions](#9-decisions) with IDs (`D-01`…). Other documents refer to those IDs instead of repeating or inventing answers. Where a document needs a working assumption, it is labelled **"Default pending D-xx"**.

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
   - An incorrect flag gives neutral feedback ("That doesn't hold up"), reveals nothing, and carries **no penalty** (D-03). It stays in the player's list as an *unconfirmed* flag that they can revise (re-pair) or remove.
6. **Organise**: the player pins items to the evidence board, links them, writes notes, and drafts theories.
7. **Stuck?** The player may ask for an optional **tiered hint** (D-04). Hints point towards *where to look or what to compare*, never at the answer.
8. **Review & accuse**: once confident, the player reviews their investigation, answers the case's accusation questions, attaches supporting evidence, and confirms. There is **one final accusation per playthrough** (D-02).
9. **Resolve**: the player sees the outcome, rating, score breakdown, full solution and explanation, red-herring explanations, and the key evidence they missed. They may **replay** the case as a new playthrough.

All progress saves on the server after every action, for guests and account holders alike (D-01). The player can leave and resume at any time. A guest resumes in the same browser. An account holder resumes on any device.

## 5. Feature set

### 5.1 Accounts and access
| Feature | Tag | Notes |
|---|---|---|
| **Guest play**: investigate any published case with no account | Essential | D-01. Progress is saved on the server against an anonymous guest identity held in a browser cookie, so it survives reloads in the same browser |
| Accounts are **optional** | Essential | D-01. Accounts add persistent progress, cross-device access, and completion history |
| Register / log in / log out (email + password) | Essential | Session-cookie auth; see ARCHITECTURE |
| **Claim guest progress**: on register or log-in, the guest's playthroughs (in-progress and completed) move into the account | Essential | D-01. Conflict rule: D-23 |
| Gentle prompts to create an account (after the first discovery session, on results) that never block play | Essential | |
| Guest data retention: inactive guest data is purged after a period | Essential | Period: D-22 |
| Password reset via email | Essential | Email provider: D-17 |
| Profile: display name, preferences (text size, reduced motion, theme) | Essential | Guests keep preferences in browser storage only |
| Account deletion and data export | Essential | Basic privacy hygiene; guests get "Forget my progress on this browser" |
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
| Server verifies each flag against authored contradictions as soon as it's submitted; a correct flag becomes **confirmed** and unlocks content | Essential |
| Neutral feedback for incorrect flags that leaks nothing | Essential |
| **No penalties** for incorrect flags: no score deduction, no attempt limit, not shown as a failure count (D-03) | Essential |
| Incorrect flags stay in a "My flags" list as **unconfirmed**; the player can **revise** (change either side, which re-checks) or **remove** them | Essential |
| Confirmed contradictions list with authored explanation | Essential |
| Confirmed contradictions are permanent, and the leads they unlocked stay (no dead ends). Whether players may *hide* them: D-24 | Essential |

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
| **Investigation review** before accusing: confirmed contradictions, active theory, pinned board items, suspicion markers, and loose ends (unexamined evidence, unasked topics, unvisited locations, unconfirmed flags), each linking back into the workspace | Essential |
| Answer review step and explicit "final" confirmation | Essential |
| **One final accusation per playthrough** (D-02). Once it's submitted, the investigation closes and the solution is revealed | Essential |
| Outcome: **Solved** or **Unsolved**, plus rating tier (see §6) | Essential |
| Score breakdown per question with the correct answer and explanation | Essential |
| Full solution narrative ("How it happened") | Essential |
| Red herrings explained | Essential |
| "Evidence you missed": key items not discovered | Essential |
| Playthrough statistics: time spent, % evidence found, contradictions confirmed, hints used. Incorrect flags are **not** shown (D-03) | Essential |
| Replay case: starts a fresh playthrough; earlier playthroughs and results stay in history | Essential |
| Shareable spoiler-free result card | Optional (D-09) |

### 5.10 Player progress
| Feature | Tag |
|---|---|
| Progress page: cases solved, ratings, in-progress investigations, totals | Essential (guests see this browser's progress plus a prompt to create an account) |
| Playthrough history per case (completion history) | Essential |
| Detective rank based on cumulative performance | Optional |
| Achievements (e.g. "No hints used", "Found every clue") | Optional |
| Leaderboards | Optional (D-09) |

### 5.11 Hints
| Feature | Tag |
|---|---|
| **Optional, tiered hints in v1.0** (D-04). Authored per case as *hint tracks*, each with 3 tiers: **nudge** (where to focus) → **pointer** (which items to look at together) → **direction** (the exact comparison or action to make) | Essential |
| Hints guide deduction **without revealing answers**: no hint names the culprit, states a motive or method, or says "X is lying" | Essential (content rule, CASE_DESIGN §5.10) |
| The game offers hints only for tracks that are currently relevant and unresolved, and never reveals undiscovered content in hint text | Essential |
| The player requests each tier explicitly; there's a confirm step before the *direction* tier | Essential |
| Hints used are recorded and shown in results statistics | Essential |
| Whether hint use affects score or rating tier | **Open: D-21**. Default: no effect |

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
- v1.0 ships with **three complete, distinct mysteries** (D-05). Each has a different crime type, setting, and difficulty, and each includes authored hint tracks:
  1. *The Missing Masterpiece*: art theft, Standard difficulty (worked example in CASE_DESIGN).
  2. A second case with a different crime type (e.g. a disappearance or poisoning), Introductory difficulty, doubling as the tutorial case (D-18).
  3. A third case, Hard difficulty, with more suspects and 4–6 contradictions, 2–3 of them layered (CASE_DESIGN §6.1).
- Cases 2 and 3 are outlined during the roadmap's content milestones. They are not designed in this planning phase.
- **Ordinary content additions require no application code changes** (D-05). "Ordinary" means a case built from the existing mechanics: people, locations, evidence kinds, topics, reactions, timeline, contradictions, hints, and configurable accusation questions. Only a genuinely new mechanic needs code, through the extension process in ARCHITECTURE §8.

## 6. Scoring and ratings (working definition)

Each case's accusation questions carry points (defined in the case's `accusation.yaml` and `solution.yaml`). Outcome:

| Outcome | Condition |
|---|---|
| **Solved: Airtight** | All `required_for_solve` questions correct **and** score ≥ 90% |
| **Solved: Convincing** | All required questions correct **and** score ≥ 70% |
| **Solved: Shaky** | All required questions correct, score < 70% (right answer, weak proof) |
| **Unsolved** | Any required question wrong (typically: wrong culprit) |

Thresholds are global defaults that a case may override.
- **Incorrect contradiction flags never affect score** (D-03, decided).
- Whether **hint use** affects score or tier is open (D-21), and so is **elapsed time** (D-15). Until decided, neither affects score. Hint use and time appear only as statistics.

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

## 9. Decisions

The product owner settles decisions, and other documents cite them by ID. **Decided** items are requirements. **Open** items use the listed default for planning only, and each one must be settled before the milestone named in the "Needed by" column. A decision isn't renumbered when it moves from Open to Decided.

### 9.1 Decided (current requirements)

| ID | Decision | Decided | Main effects |
|---|---|---|---|
| **D-01** | **Guest play is allowed.** Players can investigate any published case without an account. Accounts are optional, and add persistent progress, cross-device access, and completion history. Guest progress is claimed into the account on register or log-in. | 2026-10-23 | Guest identity (ARCHITECTURE §5), nullable `user` on playthroughs (DATA_MODEL §5), "Player" permission (API_PLAN), guest UI states (SCREEN_DESIGN), roadmap M5/M7/M16 |
| **D-02** | **One final accusation per playthrough.** Players can review their investigation before submitting. Afterwards the solution and explanation are revealed. Players may replay the case as a new playthrough. | 2026-10-23 | Investigation review step (SCREEN_DESIGN §8), unique accusation per playthrough (DATA_MODEL), M14 |
| **D-03** | **No penalties for incorrect contradiction flags.** Players can revise or remove their flags. Interpretation: incorrect flags persist as *unconfirmed* and are editable/removable; confirmed contradictions are permanent facts (D-24 covers hiding them). | 2026-10-23 | Flags resource (API_PLAN §4.2), `play_contradictionflag` (DATA_MODEL), scoring, results stats, M10 |
| **D-04** | **Optional, tiered hints ship in v1.0.** They guide deduction without immediately revealing the answer. | 2026-10-23 | Hint tracks in case format (CASE_DESIGN §5.10), hint tables and endpoints, new milestone M15, content milestones |
| **D-05** | **Launch with three complete, distinct mysteries.** The case system supports additional cases without application code changes for ordinary content additions. | 2026-10-23 | §5.14, M17/M18 acceptance criteria |
| **D-07** | **Render** is the planned deployment platform for the Vue frontend, Django REST API, and PostgreSQL. Current pricing, service availability, and deployment requirements must be **verified before deployment**. No Render pricing or limits are assumed in these docs. | 2026-10-23 | ARCHITECTURE §7, §9; M20 |
| **D-19** | **Public GitHub repository** for portfolio visibility. Develop locally first; exclude secrets and generated files; provide `.env.example` without real credentials; configure CI before relying on automated checks. | 2026-10-23 | README, ARCHITECTURE §9, roadmap M0.1 (licensing & publication prep) |
| **D-20** | **Licensing:** MIT for application code. Original mystery narratives and case content are under a separate, clearly documented copyright policy (all rights reserved) unless the owner explicitly chooses to license content for reuse. | 2026-10-23 | `LICENSE`, `content/COPYRIGHT.md`, README §License, CASE_DESIGN §7 |
| **D-23** | **Guest-claim conflict:** if the account already has an in-progress playthrough of a case the guest also has in progress, keep both. The more recently active one stays in progress, the other becomes *abandoned* (still in history), and the player is told which was kept. | 2026-10-23 (default accepted) | `accounts/claim.py`, API `claimed.conflicts`, M7/M16 |
| **D-25** | **Spoilers in the public repo are accepted for v1.0.** Case solutions under `content/cases/*/spoilers/` stay in the public repository, with prominent spoiler warnings in the README and `content/README.md`. Revisit if it becomes a problem. | 2026-10-23 (default accepted) | README, `content/README.md`, CASE_DESIGN §7.2 |
| **D-27** | **`docs/` licensing:** technical documentation is MIT. The case narrative excerpts in CASE_DESIGN §9–10 fall under the content copyright policy. | 2026-10-23 (default accepted) | `LICENSE` scope note, `content/COPYRIGHT.md` |

### 9.2 Open

| ID | Question | Planning default | Needed by |
|---|---|---|---|
| **D-06** | Business model: free, one-time purchase, case packs, subscription? | Free, no payments in v1.0 | M20 |
| **D-08** | Ship a light theme in v1.0? | Dark theme only in v1.0; tokens support a second theme | M19 |
| **D-09** | Public leaderboards or shareable result cards? | Neither in v1.0 | Post-1.0 |
| **D-10** | Who authors cases long-term: only the core team via YAML, or invited authors via an in-app editor? | Core team via YAML | Post-1.0 |
| **D-11** | Use an LLM for free-form interviews in future? | No; authored topics only | Post-1.0 |
| **D-12** | Ambient audio and sound effects? | Not in v1.0 | M19 |
| **D-13** | Phone support level? | Full play on all sizes; phones get list-based board and timeline | M19 (affects M9–M12 layouts) |
| **D-14** | When a published case is updated, what happens to in-progress playthroughs? | Additive changes apply live; breaking changes blocked while playthroughs are in progress (ARCHITECTURE §8) | M4 |
| **D-15** | Should elapsed time or number of actions affect score? | No; shown as statistics only | M14 |
| **D-16** | Content tone and age rating: are murders and violence allowed, and how graphic? | Non-graphic; violence off-screen; content notes on briefing | M17 |
| **D-17** | Transactional email provider (password reset, verification)? Require email verification? | Provider TBD (verify availability alongside Render); verification optional in v1.0; console email backend until M20 | M20 |
| **D-18** | Dedicated interactive tutorial, or does the Introductory case teach through contextual tips? | Introductory case plus dismissible contextual tips | M18 |
| **D-21** | Does hint use affect score or rating tier? (e.g. cap at Convincing if the *direction* tier was used) | No effect on score or tier; hints shown in statistics | M14 |
| **D-22** | How long is inactive guest data kept? | Guest cookie lasts 90 days; guest playthroughs inactive for 90 days are purged by a scheduled job | M16 |
| **D-24** | Can players hide a *confirmed* contradiction from their lists? (Its unlocks always remain.) | No; confirmed contradictions are permanent and always listed | M10 |
| **D-26** | Render topology: one Web Service serving both the API and the built Vue SPA (same origin), or a Render Static Site for Vue plus a Web Service for the API? | One Web Service + Render PostgreSQL (simplest cookie/CSRF story). The split option needs a shared custom domain; see ARCHITECTURE §9 | M20 (verify in an early spike, M1) |
| **D-28** | When to create the public GitHub repository and push for the first time? | Only when the owner explicitly asks; recommended before M1 so CI runs from the first code milestone | Before M1 |
