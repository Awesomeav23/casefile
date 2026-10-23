# Casefile Case Content

> ## ⚠️ Spoiler warning
> Each case folder contains a `spoilers/` directory with the **solution, contradictions, and hints**. If you want to play a case fairly, don't open those files, or this folder, before you've finished it.

## Layout

```
content/cases/
├── _template/      # starting point for a new case (planned, M3)
├── _fixtures/      # tiny test cases used by automated tests (planned, M3)
└── <case-slug>/    # one folder per mystery
    ├── case.yaml, people.yaml, locations.yaml, evidence.yaml,
    │   interviews.yaml, timeline.yaml, accusation.yaml   # player-visible once discovered
    ├── spoilers/   # contradictions.yaml, hints.yaml, solution.yaml (SPOILERS)
    └── assets/     # images + CREDITS.md
```

No cases exist yet. *The Missing Masterpiece* is planned for M3 (skeleton) and M17 (complete).

## Authoring

The format, fairness rules, and hint standards are in [`docs/CASE_DESIGN.md`](../docs/CASE_DESIGN.md). Adding an ordinary case requires no application code. Validate it with `manage.py validate_case` (planned, M3).

## Copyright

Case content is **© Avnish Ozarkar, all rights reserved**. It is not covered by the repository's MIT License. See [`COPYRIGHT.md`](COPYRIGHT.md).
