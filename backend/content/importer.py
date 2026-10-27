"""Import a validated case folder into the content tables (docs/ARCHITECTURE.md §8).

- Runs the validator first; any error refuses the import and writes nothing.
- One transaction per case: a failure part-way leaves the database untouched.
- Upserts by stable key, so text edits update rows in place (same primary keys).
- An unchanged folder (same content hash) writes nothing, not even an audit row, unless it is
  being published, which is recorded.
- Breaking changes (removed keys, changed questions or answers) bump `content_version`.
  On a *published* case they are refused unless `force=True` (default pending D-14; M7
  narrows the refusal to published cases with playthroughs in progress).
"""

from __future__ import annotations

import getpass
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from play.conditions import parse, to_json
from play.engine import CaseGraph

from . import models as m
from .assets import asset_name, folder_hash
from .compile import build_graph, typed_ref, world_time
from .loader import load_case
from .schema import CaseBundle
from .validator import validate_case


class ImportRefused(Exception):
    def __init__(self, slug: str, reasons: list[str]):
        self.slug, self.reasons = slug, reasons
        super().__init__(f"{slug}: import refused:\n" + "\n".join(f"  {r}" for r in reasons))


@dataclass
class ImportResult:
    slug: str
    action: str  # created | updated | published | unchanged
    breaking: bool
    content_version: int
    status: str
    warnings: list[str] = field(default_factory=list)


def import_case(
    folder: Path, *, publish: bool = False, force: bool = False, imported_by: str | None = None
) -> ImportResult:
    folder = folder.resolve()
    report = validate_case(folder)
    if not report.ok:
        raise ImportRefused(folder.name, [str(i) for i in report.errors])
    warnings = [str(i) for i in report.warnings]
    bundle, _ = load_case(folder)
    assert bundle is not None  # validated above
    slug, digest = bundle.case.slug, folder_hash(folder)

    with transaction.atomic():
        case = m.Case.objects.select_for_update().filter(slug=slug).first()
        if case and case.content_hash == digest:
            if publish and case.status != "published":
                _publish(case)
                case.save()
                m.CaseImport.objects.create(
                    case=case,
                    imported_by=imported_by or getpass.getuser(),
                    content_hash=digest,
                    content_version=case.content_version,
                    report={"warnings": warnings, "breaking": [], "published": True},
                )
                return ImportResult(
                    slug, "published", False, case.content_version, case.status, warnings
                )
            return ImportResult(
                slug, "unchanged", False, case.content_version, case.status, warnings
            )

        reasons = breaking_changes(case, bundle) if case else []
        if reasons and case.status == "published" and not force:
            raise ImportRefused(
                slug, [f"breaking change to a published case (use --force): {r}" for r in reasons]
            )

        created = case is None
        case = _write(case, bundle, folder, digest, bump=bool(reasons))
        if publish:
            _publish(case)
            case.save()
        m.CaseImport.objects.create(
            case=case,
            imported_by=imported_by or getpass.getuser(),
            content_hash=digest,
            content_version=case.content_version,
            breaking=bool(reasons),
            report={"warnings": warnings, "breaking": reasons},
        )
    action = "created" if created else "updated"
    return ImportResult(slug, action, bool(reasons), case.content_version, case.status, warnings)


def _publish(case: m.Case) -> None:
    case.status = "published"
    case.published_at = case.published_at or timezone.now()


# --- breaking-change detection -------------------------------------------------------------


def _bundle_keys(b: CaseBundle) -> dict[str, set[str]]:
    keys = {
        "person": {p.key for p in b.people},
        "location": {x.key for x in b.locations},
        "evidence": {e.key for e in b.evidence},
        "timeline_event": {t.key for t in b.timeline},
        "contradiction": {c.key for c in b.contradictions},
        "question": {q.key for q in b.accusation.questions},
        "option": {f"{q.key}/{o.key}" for q in b.accusation.questions for o in q.options or []},
        "hint_track": {h.key for h in b.hints},
        "topic": set(),
        "statement": set(),
    }
    for person, interview in b.interviews.items():
        keys["topic"] |= {f"{person}/{t.key}" for t in interview.topics}
        statements = [s for t in interview.topics for s in t.statements]
        statements += [s for r in interview.reactions for s in r.statements]
        keys["statement"] |= {f"{person}/{s.key}" for s in statements}
    return keys


def _db_keys(case: m.Case) -> dict[str, set[str]]:
    def plain(model):
        return set(model.objects.filter(case=case).values_list("key", flat=True))

    def scoped(model, parent):
        rows = model.objects.filter(case=case).values_list(f"{parent}__key", "key")
        return {f"{a}/{b}" for a, b in rows}

    return {
        "person": plain(m.Person),
        "location": plain(m.Location),
        "evidence": plain(m.Evidence),
        "timeline_event": plain(m.TimelineEvent),
        "contradiction": plain(m.Contradiction),
        "question": plain(m.AccusationQuestion),
        "option": {
            f"{q}/{o}"
            for q, o in m.AccusationOption.objects.filter(question__case=case).values_list(
                "question__key", "key"
            )
        },
        "hint_track": plain(m.HintTrack),
        "topic": scoped(m.Topic, "person"),
        "statement": scoped(m.Statement, "person"),
    }


def _answer_signature(correct, points, proof_points, full, partial) -> tuple:
    return (correct, points, proof_points, full, partial)


def breaking_changes(case: m.Case, b: CaseBundle) -> list[str]:
    reasons: list[str] = []
    old, new = _db_keys(case), _bundle_keys(b)
    for kind in old:
        for key in sorted(old[kind] - new[kind]):
            reasons.append(f"{kind} '{key}' removed")
    questions = {q.key: q for q in b.accusation.questions}
    for q in m.AccusationQuestion.objects.filter(case=case).select_related("answer_key"):
        if q.key not in questions:
            continue
        nq = questions[q.key]
        if (q.kind, q.required_for_solve) != (nq.kind, nq.required_for_solve):
            reasons.append(f"question '{q.key}' changed kind or required_for_solve")
        spec = b.solution.answers.get(q.key)
        ak = getattr(q, "answer_key", None)
        if spec is None or ak is None:
            continue
        before = _answer_signature(
            ak.correct_value, ak.points, ak.proof_points, ak.proof_full, ak.proof_partial
        )
        if before != _answer_signature(*_answer_fields(spec)):
            reasons.append(f"answer for '{q.key}' changed")
    return reasons


def _answer_fields(spec) -> tuple:
    proof = spec.proof
    full = [[typed_ref(r) for r in g] for g in proof.full] if proof else []
    partial = [[typed_ref(r) for r in g] for g in proof.partial] if proof else []
    return (spec.correct, spec.points, proof.points if proof else 0, full, partial)


# --- writing ------------------------------------------------------------------------------


def _upsert(model, lookup: dict, values: dict):
    obj, _ = model.objects.update_or_create(**lookup, defaults=values)
    return obj


def _prune(queryset, keep: list) -> None:
    queryset.exclude(pk__in=[o.pk for o in keep]).delete()


def _write(case: m.Case | None, b: CaseBundle, folder: Path, digest: str, *, bump: bool) -> m.Case:
    graph = build_graph(b)
    c, slug = b.case, b.case.slug
    case = case or m.Case(slug=slug, content_version=1)
    if bump and case.pk:
        case.content_version += 1
    for name, value in {
        "title": c.title,
        "tagline": c.tagline,
        "difficulty": c.difficulty,
        "estimated_minutes": c.estimated_minutes,
        "tags": c.tags,
        "content_notes": c.content_notes,
        "world_date": c.setting.world_date,
        "era_note": c.setting.era_note or "",
        "cover_image": asset_name(folder, c.cover_image, slug),
        "cover_alt": c.cover_alt,
        "briefing": c.briefing,
        "objective": c.objective,
        "accusation_intro": b.accusation.intro or "",
        "copyright": c.copyright,
        "rating_thresholds": c.rating_thresholds.model_dump() if c.rating_thresholds else None,
        "format_version": c.format_version,
        "content_hash": digest,
    }.items():
        setattr(case, name, value)
    case.save()

    ctx = _Context(case, b, graph, folder)
    ctx.people()
    ctx.locations()
    ctx.evidence()
    ctx.interviews()
    ctx.timeline()
    ctx.accusation()
    ctx.contradictions()
    ctx.solution()
    _import_hints(ctx)
    ctx.prune()
    return case


class _Context:
    def __init__(self, case: m.Case, b: CaseBundle, graph: CaseGraph, folder: Path):
        self.case, self.b, self.graph, self.folder = case, b, graph, folder
        self.kept: dict[type, list] = {}
        self.person: dict[str, m.Person] = {}
        self.location: dict[str, m.Location] = {}
        self.evidence_rows: dict[str, m.Evidence] = {}
        self.statement: dict[str, m.Statement] = {}

    def keep(self, obj):
        self.kept.setdefault(type(obj), []).append(obj)
        return obj

    def requires(self, item_type: str, ref: str):
        """The item's effective condition, as stored JSON."""
        return to_json(self.graph.items[(item_type, ref)])

    def image(self, rel: str | None) -> str:
        return asset_name(self.folder, rel, self.case.slug) if rel else ""

    def time(self, value: str | None):
        return world_time(value, self.b.case.setting.world_date) if value else None

    def people(self):
        for i, p in enumerate(self.b.people):
            self.person[p.key] = self.keep(
                _upsert(
                    m.Person,
                    {"case": self.case, "key": p.key},
                    {
                        "sort_order": i,
                        "name": p.name,
                        "role": p.role,
                        "summary": p.summary,
                        "bio": p.bio or "",
                        "default_reaction": p.default_reaction,
                        "is_suspect": p.is_suspect,
                        "portrait": self.image(p.portrait),
                        "portrait_alt": p.portrait_alt or "",
                        "requires": self.requires("person", p.key),
                    },
                )
            )

    def locations(self):
        for i, x in enumerate(self.b.locations):
            self.location[x.key] = self.keep(
                _upsert(
                    m.Location,
                    {"case": self.case, "key": x.key},
                    {
                        "sort_order": i,
                        "name": x.name,
                        "description": x.description,
                        "image": self.image(x.image),
                        "image_alt": x.image_alt or "",
                        "requires": self.requires("location", x.key),
                    },
                )
            )

    def evidence(self):
        for i, e in enumerate(self.b.evidence):
            row = self.keep(
                _upsert(
                    m.Evidence,
                    {"case": self.case, "key": e.key},
                    {
                        "sort_order": i,
                        "title": e.title,
                        "kind": e.kind,
                        "summary": e.summary,
                        "body": e.body,
                        "location": self.location.get(e.location) if e.location else None,
                        "image": self.image(e.image),
                        "image_alt": e.image_alt or "",
                        "requires": self.requires("evidence", e.key),
                    },
                )
            )
            row.people.set([self.person[p] for p in e.people])
            self.evidence_rows[e.key] = row

    def _statement(self, person, s, order, *, topic=None, reaction=None):
        claim = s.claim
        self.statement[f"{person.key}/{s.key}"] = self.keep(
            _upsert(
                m.Statement,
                {"person": person, "key": s.key},
                {
                    "case": self.case,
                    "sort_order": order,
                    "text": s.text,
                    "topic": topic,
                    "reaction_evidence": reaction,
                    "claim_from": self.time(claim.from_) if claim else None,
                    "claim_to": self.time(claim.to) if claim else None,
                    "claim_location": self.location.get(claim.location)
                    if claim and claim.location
                    else None,
                },
            )
        )

    def interviews(self):
        order = 0
        for person_key, interview in self.b.interviews.items():
            person = self.person[person_key]
            for t in interview.topics:
                order += 1
                topic = self.keep(
                    _upsert(
                        m.Topic,
                        {"person": person, "key": t.key},
                        {
                            "case": self.case,
                            "sort_order": order,
                            "prompt": t.prompt,
                            "requires": self.requires("topic", f"{person_key}/{t.key}"),
                        },
                    )
                )
                for s in t.statements:
                    order += 1
                    self._statement(person, s, order, topic=topic)
            for r in interview.reactions:
                for s in r.statements:
                    order += 1
                    self._statement(person, s, order, reaction=self.evidence_rows[r.evidence])

    def _side(self, item):
        item_type, ref = item
        if item_type == "evidence":
            return {"evidence": self.evidence_rows[ref], "statement": None}
        return {"evidence": None, "statement": self.statement[ref]}

    def timeline(self):
        for i, t in enumerate(self.b.timeline):
            source = self._side(t.source.item)
            row = self.keep(
                _upsert(
                    m.TimelineEvent,
                    {"case": self.case, "key": t.key},
                    {
                        "sort_order": i,
                        "title": t.title,
                        "description": t.description or "",
                        "starts_at": self.time(t.from_),
                        "ends_at": self.time(t.to),
                        "location": self.location.get(t.location) if t.location else None,
                        "certainty": t.certainty,
                        "source_evidence": source["evidence"],
                        "source_statement": source["statement"],
                        "requires": self.requires("timeline_event", t.key),
                    },
                )
            )
            row.people.set([self.person[p] for p in t.people])

    def accusation(self):
        self.questions = {}
        for i, q in enumerate(self.b.accusation.questions):
            question = self.keep(
                _upsert(
                    m.AccusationQuestion,
                    {"case": self.case, "key": q.key},
                    {
                        "sort_order": i,
                        "prompt": q.prompt,
                        "kind": q.kind,
                        "required_for_solve": q.required_for_solve,
                        "cite_min": q.cite.min,
                        "cite_max": q.cite.max,
                        "cite_prompt": q.cite.prompt or "",
                    },
                )
            )
            options = [
                _upsert(
                    m.AccusationOption,
                    {"question": question, "key": o.key},
                    {"label": o.label, "sort_order": j},
                )
                for j, o in enumerate(q.options or [])
            ]
            _prune(m.AccusationOption.objects.filter(question=question), options)
            self.questions[q.key] = question

    def contradictions(self):
        for i, c in enumerate(self.b.contradictions):
            other = self._side(c.conflicts_with.item)
            self.keep(
                _upsert(
                    m.Contradiction,
                    {"case": self.case, "key": c.key},
                    {
                        "sort_order": i,
                        "statement": self.statement[c.statement],
                        "conflicts_evidence": other["evidence"],
                        "conflicts_statement": other["statement"],
                        "accept_also": [
                            {"type": a.item[0], "key": a.item[1]} for a in c.accept_also
                        ],
                        "explanation": c.explanation,
                    },
                )
            )

    def solution(self):
        s = self.b.solution
        for qkey, spec in s.answers.items():
            correct, points, proof_points, full, partial = _answer_fields(spec)
            _upsert(
                m.AnswerKey,
                {"question": self.questions[qkey]},
                {
                    "correct_value": correct,
                    "points": points,
                    "proof_points": proof_points,
                    "proof_full": full,
                    "proof_partial": partial,
                    "explanation": spec.explanation,
                },
            )
        _upsert(
            m.CaseSolution,
            {"case": self.case},
            {
                "summary": s.summary,
                "narrative": s.narrative,
                "key_evidence": s.key_evidence,
                "answer_terms": s.answer_terms,
                "walkthrough": s.walkthrough,
            },
        )
        herrings = [
            _upsert(
                m.RedHerring,
                {"case": self.case, "person": self.person[rh.person]},
                {
                    "suspicion": rh.suspicion,
                    "explanation": rh.explanation,
                    "cleared_by": [typed_ref(r) for r in rh.cleared_by],
                },
            )
            for rh in s.red_herrings
        ]
        _prune(m.RedHerring.objects.filter(case=self.case), herrings)

    def prune(self):
        """Remove rows whose keys disappeared, dependants first (RESTRICT-safe order)."""
        for model in (
            m.HintTrack,
            m.Contradiction,
            m.TimelineEvent,
            m.Statement,
            m.Topic,
            m.AccusationQuestion,
            m.Evidence,
            m.Location,
            m.Person,
        ):
            _prune(model.objects.filter(case=self.case), self.kept.get(model, []))


def _import_hints(ctx: _Context) -> None:
    for i, h in enumerate(ctx.b.hints):
        track = ctx.keep(
            _upsert(
                m.HintTrack,
                {"case": ctx.case, "key": h.key},
                {
                    "sort_order": i,
                    "goal": h.goal,
                    "priority": h.priority,
                    "requires": to_json(parse(h.requires)),
                    "resolved_when": to_json(parse(h.resolved_when)),
                    "mentions": [typed_ref(r) for r in h.mentions],
                },
            )
        )
        for tier, entry in enumerate(h.tiers, start=1):
            _upsert(
                m.Hint, {"track": track, "tier": tier}, {"level": entry.level, "text": entry.text}
            )
