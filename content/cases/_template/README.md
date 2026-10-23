# New case template

1. Copy this folder to `content/cases/<your-slug>/` (the folder name must equal `slug`).
2. Replace every `TODO`, and add a real `assets/cover.webp` (plus `assets/CREDITS.md`).
3. Follow `docs/CASE_DESIGN.md`: write the hidden "what really happened" first, then the evidence.
4. Validate: `backend/.venv/bin/python backend/manage.py validate_case content/cases/<your-slug>`.
   Add `--mermaid` to print the unlock graph.

This template is MIT-licensed scaffolding. Your case content is yours (see `content/COPYRIGHT.md`).
