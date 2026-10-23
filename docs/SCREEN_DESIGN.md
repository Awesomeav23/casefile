# Casefile: Screen Design

**Status:** Planning draft. Layouts are described in text and wireframes. Final visuals follow [UI_UX_GUIDELINES](UI_UX_GUIDELINES.md).
**Related:** [PRODUCT_SPEC](PRODUCT_SPEC.md) · [API_PLAN](API_PLAN.md) · [ARCHITECTURE §4](ARCHITECTURE.md#4-frontend)

Breakpoints (from UI_UX_GUIDELINES §8): **phone** < 768px · **tablet** 768–1199px · **desktop** ≥ 1200px.

---

## 1. Navigation map

```
                    ┌─────────────┐
                    │  Landing  / │
                    └──────┬──────┘
          ┌────────────────┼──────────────────┐
          ▼                ▼                  ▼
   Login / Register   Case Library /cases   Player Progress /progress
   /login /register        │                         │
   /reset-password         ▼                         │
                    Case Briefing /cases/:slug ◄──────┘
                           │ Start / Resume / Replay
                           ▼
        ┌──────── Investigation Workspace /play/:id ─────────┐
        │  Overview · Locations · Evidence · People ·        │
        │  Timeline · Board · Theories      ── Accuse ──┐    │
        │  (Notebook drawer and Search on every tab)    │    │
        └───────────────────────────────────────────────┼────┘
                                                        ▼
                                     Final Accusation /play/:id/accuse
                                                        │ confirm
                                                        ▼
                                       Case Results /play/:id/results
                                                        │
                                       Library · Replay · Progress
Global: Settings /settings · 404 · error screen
```

| Route | Screen | Access (Owner = the current player, guest or account; D-01) |
|---|---|---|
| `/` | Landing | Public |
| `/login`, `/register`, `/reset-password` | Auth screens | Public |
| `/cases` | Case Library | Public (status shown for guests and accounts) |
| `/cases/:slug` | Case Briefing | Public; starting a case needs no account (a guest identity is created) |
| `/play/:id/overview` (default) | Workspace: Overview | Owner |
| `/play/:id/locations[/:key]` | Workspace: Locations | Owner |
| `/play/:id/evidence[/:key]` | Workspace: Evidence | Owner |
| `/play/:id/people[/:key]` | Workspace: People / Suspect Profile | Owner |
| `/play/:id/timeline` | Workspace: Timeline | Owner |
| `/play/:id/board` | Workspace: Evidence Board | Owner |
| `/play/:id/theories[/:theoryId]` | Workspace: Theories | Owner |
| `/play/:id/accuse` | Final Accusation | Owner, in progress |
| `/play/:id/results` | Case Results | Owner, accused |
| `/progress` | Player Progress | Player (guest or account) |
| `/settings` | Settings & Account | Player; the Account section needs an account |

Redirect rules:
- An accused playthrough's workspace routes go to `/results`.
- `/results` before accusation goes to `/overview`.
- Stale playthroughs show the "This case was updated" interstitial (ARCHITECTURE §8).

## 2. Common states (apply to every screen)

| State | Treatment |
|---|---|
| Loading | Skeleton placeholders shaped like the final content. No full-screen spinners after first load |
| Empty | Illustrated empty state with one-line guidance and a primary action |
| Error (network) | Inline message + "Try again"; existing content stays visible |
| Error (404 / not owner) | Full 404 screen: "This file doesn't exist or isn't yours." + link to library |
| Offline | Persistent top banner; actions disabled with tooltip "Reconnect to continue investigating" |
| Guest (D-01) | Small, dismissible-per-session banner in the workspace and on Progress: "Playing as a guest. Your progress is saved in this browser. **Create an account** to keep it across devices." It never blocks play. Dismissed for the session after 1 click |
| Saving (board, notes, theories) | Subtle "Saving… / Saved" indicator; 409 conflict shows a "Reload latest" dialog |

---

## 3. Landing `/`

**Purpose:** convey the fantasy in five seconds and get the player into a case.

```
┌──────────────────────────────────────────────────────────┐
│ CASEFILE                                  Cases  Log in  │
├──────────────────────────────────────────────────────────┤
│  [atmospheric hero: desk, case folder, lamp light]       │
│  Every case has an answer. Prove it.                     │
│  [ Browse cases ]   [ How it works ]                     │
├──────────────────────────────────────────────────────────┤
│  How it works: 1 Investigate · 2 Question · 3 Expose · 4 Accuse │
├──────────────────────────────────────────────────────────┤
│  Featured case card(s)  →  Briefing                      │
├──────────────────────────────────────────────────────────┤
│  Fair-play promise · footer                              │
└──────────────────────────────────────────────────────────┘
```
- Returning players (account **or** guest) see "Continue investigation" for their most recent in-progress playthrough instead of the hero CTA.
- The primary CTA always leads straight into play. No sign-up wall appears anywhere before a case (D-01).
- "How it works" is four illustrated steps that match the gameplay loop (PRODUCT_SPEC §4).
- Connects to: Library, Briefing (featured), Login/Register, Workspace (continue).

## 4. Auth screens

- A centred card on a desk-texture background. Fields: email, password (with show toggle), display name (register).
- Inline validation on blur; server errors map to fields. The submit button shows a busy state.
- After login or register, redirect to `next` or the Library. If guest progress was claimed, show a notice: "We moved 2 investigations from this browser into your account." If a D-23 conflict occurred, add one line per case saying which playthrough was kept, with a link to History.
- Register and login screens explain the benefit in one line: "Keep your progress across devices and build your case history."
- Password reset: request form → "Check your email" confirmation (same message whether or not the account exists) → token form.

## 5. Case Library `/cases`

**Purpose:** choose a case.

```
┌─ Filters ───────────────┐ ┌──────────────────────────────────────┐
│ Status: All ▾           │ │ ┌──────┐ ┌──────┐ ┌──────┐           │
│ Difficulty: ☐ Intro     │ │ │cover │ │cover │ │cover │           │
│   ☐ Standard ☐ Hard     │ │ │Title │ │Title │ │Title │           │
│ Tags: theft · murder …  │ │ │●●○ 60m│ │●○○ 30m│ │●●● 90m│        │
│ Sort: Newest ▾          │ │ │[In progress]│[Solved ★ Airtight]   │
└─────────────────────────┘ └──────────────────────────────────────┘
```
- **Case card**: cover, title, tagline, difficulty pips + label, estimated time, tags, and a status ribbon (`New`, `In progress`, `Solved · tier`, `Unsolved`). The whole card is one link to the Briefing.
- Filters collapse into a "Filter" sheet on phone. Filter state lives in the URL query.
- Empty state (no filter matches): "No cases match. Clear filters."
- Connects to: Briefing.

## 6. Case Briefing `/cases/:slug`

**Purpose:** set the scene and the objective, then start.

```
┌──────────────────────────────────────────────────────────┐
│ ← Library                                                │
│ [cover image, full-bleed with vignette]                  │
│ THE MISSING MASTERPIECE         Standard · ~60 min       │
│ Content notes: none                                      │
├───────────────────────────────┬──────────────────────────┤
│ BRIEFING (typeset dossier)    │ OBJECTIVE                │
│ On the evening of Friday …    │ Determine who, how, why, │
│                               │ and where it is now.     │
│                               │ PERSONS OF INTEREST      │
│                               │ [portrait] Vivian Ashcombe│
│                               │ [portrait] …             │
│                               │ [ Begin investigation ]  │
└───────────────────────────────┴──────────────────────────┘
```
- Primary CTA by status: **Begin investigation** (not started) / **Resume investigation** + secondary "Start over" (in progress, which confirms abandoning) / **Replay case** + "View results" (accused).
- No account: the CTA is still **Begin investigation** (guest play, D-01), with a secondary text link "Log in to save across devices".
- The briefing footer shows the case's copyright line (D-20).
- Playthrough history (if any): a compact list of past outcomes.
- The briefing stays reachable from the workspace (Overview → "Re-read briefing").

## 7. Investigation Workspace `/play/:id/*`

### 7.1 Shell

```
Desktop
┌──────────────────────────────────────────────────────────────────────┐
│ ◧ CASEFILE │ The Missing Masterpiece  [🔍 ⌘K] [💡 Hint] [Notebook] [≡]│
├────────────┬─────────────────────────────────────────────┬───────────┤
│ Overview   │                                             │ Notebook  │
│ Locations 2│              Active section                 │ drawer    │
│ Evidence  5│                                             │ (toggle)  │
│ People    1│                                             │           │
│ Timeline   │                                             │           │
│ Board      │                                             │           │
│ Theories   │                                             │           │
│ ───────── │                                             │           │
│ [ Accuse ] │                                             │           │
└────────────┴─────────────────────────────────────────────┴───────────┘
Phone: top bar (title, search, notebook) + bottom tab bar
       [Overview][Evidence][People][Timeline][More ▸ Locations, Board, Theories, Accuse]
```
- **Left rail** numbers = count of *new, unseen* items in that section (never totals).
- **Search (⌘K / Ctrl+K)**: a command palette over discovered items (people, evidence, statements, events, notes). Selecting an item navigates to it.
- **Notebook drawer**: notes list + editor. "Attach to current item" is prefilled when an item is open. On tablet it slides over; on phone it opens full screen.
- **Discovery toast** (bottom-right, stacked): "New evidence: *Courier Confirmation*" with a "View" link. A screen-reader live region announces the same text.
- **Item actions** (available on every evidence card, statement, and event): `Pin to board`, `Add note`, `Flag contradiction` (statements and evidence), `Present to…` (evidence).
- **Hint button** (💡): opens the Hint panel (§7.10). It shows a dot when a hint track is offered, never a count.
- **Exit / menu**: back to library, settings, abandon case (confirm dialog), and "Save progress to an account" for guests.

### 7.2 Overview

- Case header with briefing summary and "Re-read briefing".
- **Objective checklist**: the accusation questions as plain prompts (no indication of progress or correctness).
- **Discovery feed**: reverse-chronological log ("Visited the Security Office → found 3 items"). Each entry links to its item.
- **Leads**: topics available but not yet asked, locations not yet visited, evidence discovered but not yet examined. These are already-discovered things only, so showing them is not a hint.
- Contextual tips for first-time players (dismissible; D-18).

### 7.3 Locations

```
┌─ Locations ───────┐ ┌─ The Security Office ─────────────────────────┐
│ ● Main Hall    ✓  │ │ [location image]                               │
│ ● Security Off. ✓ │ │ A cramped room behind the reception desk…      │
│ ○ Loading Bay  new│ │ FOUND HERE                                    │
│ …                 │ │ [Alarm log] [CCTV index] [Insurance rider]    │
└───────────────────┘ └────────────────────────────────────────────────┘
```
- Unvisited locations show a **Visit** button. Visiting fires `visit_location`, plays a short "searching" transition (skipped under reduced motion), and lists the items found.
- Visited locations show ✓ and their found evidence. Newly unlocked evidence at an already-visited location appears with a "new" badge.
- Phone: list → detail as two screens.

### 7.4 Evidence (list + viewer)

- **List**: grid or list toggle. Filters: kind, location, person, unexamined, new. Sort: discovered order or alphabetical.
- **Viewer** (`/evidence/:key`), opened as a full panel:
  - Header: title, kind badge, where found, related people.
  - Body rendered by `kind`: **document/correspondence** on paper styling; **record** in monospace table style; **photo** in a zoomable image with caption and alt text; **object** as an image plus an examination description; **transcript** in a speaker-labelled layout.
  - Opening the viewer fires `examine_evidence` (once). Anything newly unlocked appears as toasts.
  - Actions: Pin, Note, Flag contradiction, Present to… (person picker), Cite in theory.
  - Prev/next navigation through the current filtered list.
- Empty state: "Nothing here yet. Visit a location to start gathering evidence."

### 7.5 People directory & Suspect Profile `/people/:key`

**Directory**: cards with portrait, name, role, suspect/witness tag, and the player's suspicion marker (0–3 magnifier icons, set by the player only).

**Profile / interview room**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ [portrait] CORINNE BLAKE · Senior Curator   Suspicion: 🔍🔍○ (yours) │
├──────────────────────┬────────────────────────────┬──────────────────┤
│ PROFILE              │ INTERVIEW LOG              │ ASK ABOUT        │
│ Bio                  │ You: Ask about her talk…   │ • Her talk    ✓  │
│ Linked evidence      │ CB: "I was at the lectern  │ • The alarm test │
│ Timeline claims      │      until ten…"  [⋯]      │ • The buyer  new │
│ Your notes           │ You present: Guest photo   │                  │
│                      │ CB: "Phones take odd…" [⋯] │ [Present evidence]│
└──────────────────────┴────────────────────────────┴──────────────────┘
```
- **Ask about**: lists available topics. Asked topics show ✓ and remain re-askable (the log scrolls to the earlier answer, so no duplicate log entry). New topics show a badge.
- **Present evidence**: opens a searchable picker of discovered evidence. The result appends to the log. Pairings that produce a generic default response are marked in the log as "no reaction" so the player doesn't re-present them.
- **Interview log**: chronological record for this person. Each statement has a `⋯` menu: Flag contradiction, Pin, Note, Cite.
- Statements appear with a brief typewriter reveal (instant under reduced motion; skippable by click or key).
- Phone: tabs within the profile: Interview · Profile · Topics.

### 7.6 Flag Contradiction dialog (from any statement or evidence)

```
┌ Flag a contradiction ───────────────────────────────────┐
│ STATEMENT                                               │
│  "I was at the lectern from half past nine until ten."  │
│   — Corinne Blake            [change]                   │
│ CONFLICTS WITH                                          │
│  [ Search evidence or statements…           ▾ ]         │
│  ▣ Guest Phone Photo (Main Hall, 21:51)                 │
│                                [Cancel] [Flag it]       │
└─────────────────────────────────────────────────────────┘
```
- Opened from a statement: the statement is prefilled. Opened from evidence: the evidence is prefilled and the player picks the statement.
- **Correct** → the dialog transforms into a "Contradiction found" card with the authored explanation and the list of what it unlocked. A distinct stamp animation plays and a toast follows.
- **Incorrect** → inline "That doesn't hold up." No other information is given, and there's **no penalty** (D-03). The flag is saved as *unconfirmed*. The dialog offers **Change pairing** (revise and re-check) or **Remove flag**, or the player can close it and keep the flag for later.
- **My flags** (a tab within Overview's contradictions panel): every flag the player has made.
  - *Confirmed* flags show the stamp and explanation and can't be edited or removed (their unlocks are permanent; D-24).
  - *Unconfirmed* flags show "Not confirmed" in neutral styling (no red, no failure count), with **Revise** and **Remove** actions.
- Confirmed contradictions are also listed on each involved person's profile.

### 7.7 Timeline `/timeline`

```
          21:30     21:40     21:50     22:00     22:10
Corinne   [== talk (claimed) ==========]
Daniel    [== monitors (claimed) ======]
            [smoke break (verified)]
Felix         [== courtyard (verified) ==========]
Events                 ◆21:47 sensor bypass  ◆21:51 photo
```
- **Lanes per person**, plus an "Events" lane for things not tied to a person. Filters: people, locations, certainty.
- **Claimed** events render with a dashed outline and the speaker's name. **Verified** events render solid with an evidence icon.
- Overlapping placements of one person appear naturally (two bars in one lane). They are **not** highlighted.
- Click an event → popover with source + "Open source", "Flag contradiction", "Pin".
- Zoom (15 min ↔ full day) and horizontal scroll; keyboard: arrows move focus between events.
- **Phone / screen-reader alternative**: chronological list grouped by hour, with the same data (PRODUCT_SPEC D-13).
- Empty: "No events yet. Statements with times and time-stamped evidence appear here."

### 7.8 Evidence Board `/board`

```
┌ Toolbar: [+ Add item] [+ Note card] [Link mode] [Zoom −/+] [Fit] [List view] ┐
│                                                                              │
│   [Alarm log]────contradicts────["I never touch the system"]                 │
│        │                                                                     │
│   places at scene                                                            │
│        │                                                                     │
│   [Corinne Blake]          [note: where's the canvas?]                       │
└──────────────────────────────────────────────────────────────────────────────┘
```
- **Add item**: a picker of discovered items (or drag from the "Pin" action anywhere in the workspace).
- **Move**: drag, or select + arrow keys (Shift = larger steps).
- **Link**: link mode → select source → select target → choose a label (`contradicts`, `supports`, `places at scene`, `motive for`, custom). Keyboard: select a card, press `L`, choose the target from a list.
- Card types are styled by item type: evidence = photo/document thumbnail; person = portrait; statement = quote card; note = index card; event = time tag.
- Double-click/Enter on a card opens its source.
- **List view** (default on phone): cards grouped, with links shown as "→ contradicts → …" rows. It is fully editable.
- Auto-saves (debounced) with a "Saved" indicator. A version conflict prompts a reload.
- Empty: "Pin evidence, statements, and people here to work out how they connect."

### 7.9 Theories `/theories`

- **List** of theory cards: title, suspect portrait, status (active/discarded), last edited.
- **Editor**: title; suspect (picker of discovered suspects, optional); Opportunity, Method, Motive (free text); Supporting items (citations picker, displayed as chips linking to sources); Open questions.
- Actions: Duplicate, Discard/Restore, Delete (confirm), **Use for accusation** (opens the accusation with the suspect and citations prefilled).
- Theories carry no correctness indicator (PRODUCT_SPEC §3.4).
- Empty: "Write down what you think happened. You can keep several theories and drop the ones that don't fit."

### 7.10 Hint panel (D-04)

```
┌ Hints ─────────────────────────────────────── ✕ ┐
│ Test the curator's account of the evening.      │
│  ① Nudge   Corinne was confident about where…   │
│  ② Pointer [ Show pointer ]                     │
│  ③ Direction (locked until pointer is shown)    │
│ Other open lines of inquiry ▾                    │
│  • Who touched the alarm system?                 │
└─────────────────────────────────────────────────┘
```
- Opens as a side sheet (bottom sheet on phone). It shows the **suggested** track first, and other offered tracks are collapsed below it.
- Each tier needs an explicit click. The **direction** tier asks: "This will tell you exactly what to compare. Show it?" [Not yet] [Show].
- Revealed tiers stay visible. Resolved tracks move to a "Solved with help" list.
- No hint available: "You've got everything you need for now. Try reviewing your statements against the timeline." Generic copy that is never case-specific.
- Hints used are shown on results (§9). Whether they affect rating depends on D-21 (default: no).

## 8. Final Accusation `/play/:id/accuse`

**Purpose:** a deliberate, weighty, reviewable submission.

**Flow:** Investigation review → Intro → one step per question → Answer review → Confirm → Results. There is **one accusation per playthrough** (D-02).

**Investigation review** (first step; D-02):
- Summary of the player's own work: confirmed contradictions, active theory (with "Start from this theory"), pinned board items, and suspicion markers.
- **Loose ends**: discovered but unexamined evidence, unasked topics, unvisited locations, and unconfirmed flags. Each one links back into the workspace. This list contains only already-discovered things, so it doesn't count as a hint.
- Actions: [Keep investigating] (returns to the workspace) · [I'm ready to accuse].

```
┌ Step 3 of 5 ───────────────────────────────────────────────┐
│ How was the painting removed without the alarm?            │
│ ○ The security guard switched the alarm off.               │
│ ● A maintenance override bypassed the East Room sensor.    │
│ ○ The painting was swapped for a copy before the preview.  │
│ ○ An outsider entered through the courtyard window.        │
│ PROVE IT  (cite 1–2)   [+ Cite evidence]                   │
│ [Alarm System Event Log ✕]                                 │
│                                  [Back]  [Next]            │
└────────────────────────────────────────────────────────────┘
```
- **Intro**: "You get one accusation for this investigation. Afterwards the full solution is revealed, and you can replay the case any time." Plus optional "Start from theory".
- **Person** questions show portraits of discovered suspects. **Choice** questions use radio cards. **Evidence** questions show only the citation picker.
- **Citation picker**: searchable discovered evidence, statements, and found contradictions, with previews. It enforces min/max.
- **Review**: all answers and citations on one page, each with "Edit".
- **Confirm dialog**: "Submit your accusation? You can't change it afterwards." [Keep investigating] [Submit]. The Submit button requires a deliberate click and isn't the focused default.
- Drafts persist locally (per-device convenience) until submission.
- Error states: a citation that is no longer valid (should not happen) is shown inline; 409 already submitted → redirect to results.

## 9. Case Results `/play/:id/results`

```
┌────────────────────────────────────────────────────────────┐
│           [CASE CLOSED stamp]  SOLVED · AIRTIGHT           │
│                    95 / 100                                │
├────────────────────────────────────────────────────────────┤
│ YOUR CASE vs THE TRUTH (per question)                      │
│  Culprit     ✓ Corinne Blake               30/30           │
│  Opportunity ✓ 21:45 intermission proof ✓  15/15           │
│  Method      ✓ Override bypass    proof ✓  20/20           │
│  Motive      ✓ Dismissal + buyer  proof ½  15/20           │
│  Where now   — cited Return crate proof ✓  15/15           │
├────────────────────────────────────────────────────────────┤
│ WHAT REALLY HAPPENED  (narrative, illustrated)             │
│ RED HERRINGS  (each suspect: why suspicious, what cleared) │
│ CONTRADICTIONS  found 2 of 3 (now totals are allowed)      │
│ EVIDENCE YOU MISSED  [cotton gloves]                       │
│ YOUR INVESTIGATION  54 min · 19/24 evidence · 2 hints used │
├────────────────────────────────────────────────────────────┤
│ [Replay case] [Back to library] [View progress]            │
└────────────────────────────────────────────────────────────┘
```
- The reveal is sequenced: stamp → outcome → score → breakdown (staggered; instant under reduced motion).
- **Unsolved** shows "CASE UNSOLVED" in the same structure: the correct answers, the full narrative, and encouragement to replay.
- **Replay case** starts a fresh playthrough. This result stays in history.
- **Guests** see a save prompt below the outcome: "Create an account to keep this result in your case history." This is the strongest prompt in the product, and it's still dismissible.
- Incorrect flags are never shown (D-03). "Hints used" lists each track's goal and the tiers revealed.
- The results page is a permanent page that can be revisited from Progress and the Briefing.
- Spoiler-free share card (optional, D-09).

## 10. Player Progress `/progress`

- **Summary strip**: cases solved / available, airtight count, total time.
- **In progress**: cards with case, last active, and a "Resume" button.
- **Case history**: table/list of every case with best tier and the playthrough list (outcome, date, link to results).
- Optional (post-1.0): detective rank and achievements panel.
- Empty: "No cases yet. Pick your first from the library."
- **Guests** see this browser's progress with the guest banner, plus a note that guest progress is removed after the D-22 retention period of inactivity.

## 11. Settings & Account `/settings`

- Profile: display name.
- Preferences: text size (100/115/130%), reduced motion (system default or forced), theme (if D-08), contextual tips on/off.
- Account (account holders): change password, export my data, delete account (password + typed confirmation).
- Guests: preferences (stored in this browser), "Create account / Log in to keep your progress", and "Forget my progress on this browser" (confirm dialog).

## 12. Staff-only additions

- The Library shows draft cases with a "Draft" ribbon.
- A preview playthrough adds a toolbar to the workspace: "Reveal all" and "Show unlock reasons" (each item shows the `requires` condition that revealed it). Walkthroughs run in automated tests, not the UI.
- Not visible to players.
