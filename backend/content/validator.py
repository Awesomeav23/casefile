"""Case validator (docs/CASE_DESIGN.md §6.7 and §8).

Stage 1 (structure): schema (loader), conditions, references, assets, raw HTML, timeline.
Stage 2 (logic; only when stage 1 has no errors): build the unlock graph, then
  F1 answers and a full proof set reachable · F2 key/clearing evidence reachable ·
  F3 orphans (warning) · F4 culprit appears early · F5 every other suspect is a red herring ·
  every contradiction reachable · F6 walkthrough is legal and scores Airtight ·
  F12 hint tracks are offerable and only name found items · F13 hint coverage (warning) ·
  F14 hint text doesn't give answers away (warning).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from play.conditions import (
    ITEM_TYPES,
    Condition,
    ConditionError,
    Discovered,
    Fact,
    ItemKey,
    atoms,
    evaluate,
    parse,
)
from play.engine import (
    CaseGraph,
    contradiction_for,
    discover,
    guaranteed,
    reachable_without,
    simulate,
)
from play.scoring import AnswerKey, Proof, Question, Submission, Thresholds, score

from .compile import CITABLE_TYPES, build_graph, parse_ref, world_time
from .loader import load_case
from .report import Report
from .schema import CaseBundle

HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>|<!--")
WEBP_MAGIC = (b"RIFF", b"WEBP")
FACT_TARGET = {
    "visited": "location",
    "examined": "evidence",
    "asked": "topic",
    "contradiction": "contradiction",
}


def validate_case(folder: Path, *, mermaid: bool = False) -> Report:
    folder = folder.resolve()
    bundle, report = load_case(folder)
    if bundle is None:
        return report
    checker = _Checker(folder, bundle, report)
    checker.structure()
    if report.ok:
        checker.logic()
        if mermaid:
            report.mermaid = to_mermaid(checker.graph)
    return report


class _Checker:
    def __init__(self, folder: Path, bundle: CaseBundle, report: Report):
        self.folder, self.b, self.r = folder, bundle, report
        self.items: dict[str, set[str]] = {t: set() for t in ITEM_TYPES}
        self.conditions: dict[tuple[str, str], Condition] = {}  # (file, key) → parsed
        self.graph: CaseGraph | None = None

    # ------------------------------------------------------------------ stage 1: structure

    def structure(self) -> None:
        b = self.b
        if b.case.slug != self.folder.name:
            self.r.error(
                "reference",
                "case.yaml",
                "slug",
                f"slug {b.case.slug!r} must match the folder name {self.folder.name!r}",
            )
        self._index()
        self._check_conditions()
        self._check_references()
        self._check_solution()
        self._check_assets()
        self._check_html()
        self._check_timeline()

    def _index(self) -> None:
        b, items = self.b, self.items
        items["person"] = {p.key for p in b.people}
        items["location"] = {loc.key for loc in b.locations}
        items["evidence"] = {e.key for e in b.evidence}
        items["timeline_event"] = {t.key for t in b.timeline}
        items["contradiction"] = {c.key for c in b.contradictions}
        for person, interview in b.interviews.items():
            topic_keys: set[str] = set()
            for topic in interview.topics:
                if topic.key in topic_keys:
                    self.r.error(
                        "duplicate-key",
                        "interviews.yaml",
                        f"{person}/{topic.key}",
                        "topic key is used more than once for this person",
                    )
                topic_keys.add(topic.key)
                items["topic"].add(f"{person}/{topic.key}")
            statements = [s for t in interview.topics for s in t.statements] + [
                s for r in interview.reactions for s in r.statements
            ]
            seen: set[str] = set()
            for statement in statements:
                if statement.key in seen:
                    self.r.error(
                        "duplicate-key",
                        "interviews.yaml",
                        f"{person}/{statement.key}",
                        "statement key is used more than once for this person",
                    )
                seen.add(statement.key)
                items["statement"].add(f"{person}/{statement.key}")
        self.suspects = {p.key for p in b.people if p.is_suspect}
        self.questions = {q.key: q for q in b.accusation.questions}
        self.culprits = {
            spec.correct
            for key, spec in b.solution.answers.items()
            if key in self.questions
            and self.questions[key].kind == "person"
            and self.questions[key].required_for_solve
            and spec.correct
        }

    def exists(self, item: ItemKey) -> bool:
        item_type, ref = item
        return item_type in self.items and ref in self.items[item_type]

    def _sources(self) -> Iterator[tuple[str, str, str, Any]]:
        """Every authored condition: (file, key, field, raw)."""
        b = self.b
        for p in b.people:
            yield "people.yaml", p.key, "requires", p.requires
        for loc in b.locations:
            yield "locations.yaml", loc.key, "requires", loc.requires
        for e in b.evidence:
            yield "evidence.yaml", e.key, "requires", e.requires
        for person, interview in b.interviews.items():
            for t in interview.topics:
                yield "interviews.yaml", f"{person}/{t.key}", "requires", t.requires
        for ev in b.timeline:
            yield "timeline.yaml", ev.key, "requires", ev.requires
        for h in b.hints:
            yield "spoilers/hints.yaml", h.key, "requires", h.requires
            yield "spoilers/hints.yaml", h.key, "resolved_when", h.resolved_when

    def _check_conditions(self) -> None:
        for file, key, field, raw in self._sources():
            if raw is None:
                if field != "requires" or file in ("timeline.yaml", "spoilers/hints.yaml"):
                    self.r.error("condition", file, key, f"{field} is required")
                continue
            try:
                cond = parse(raw)
            except ConditionError as exc:
                self.r.error("condition", file, key, f"{field}: {exc}")
                continue
            self.conditions[(file, f"{key}#{field}")] = cond
            for atom in atoms(cond):
                problem = self._atom_problem(atom)
                if problem:
                    self.r.error("reference", file, key, f"{field}: {problem}")

    def _atom_problem(self, atom: object) -> str | None:
        if isinstance(atom, Fact):
            if atom.kind == "presented":
                person, _, evidence = atom.ref.partition("/")
                if person not in self.items["person"] or evidence not in self.items["evidence"]:
                    return f"presented: {atom.ref!r} must be <existing person>/<existing evidence>"
                return None
            target = FACT_TARGET[atom.kind]
            if atom.ref not in self.items[target]:
                return f"{atom.kind}: unknown {target} {atom.ref!r}"
        if isinstance(atom, Discovered) and not self.exists((atom.type, atom.ref)):
            return f"discovered: unknown {atom.type} {atom.ref!r}"
        return None

    def _ref(self, file: str, key: str, item: ItemKey, what: str) -> None:
        if not self.exists(item):
            self.r.error("reference", file, key, f"{what}: unknown {item[0]} {item[1]!r}")

    def _check_references(self) -> None:
        b = self.b
        for e in b.evidence:
            if e.location:
                self._ref("evidence.yaml", e.key, ("location", e.location), "location")
            for p in e.people:
                self._ref("evidence.yaml", e.key, ("person", p), "people")
        for person, interview in b.interviews.items():
            if person not in self.items["person"]:
                self.r.error("reference", "interviews.yaml", person, "unknown person")
            seen: set[str] = set()
            for reaction in interview.reactions:
                key = f"{person}/{reaction.evidence}"
                self._ref("interviews.yaml", key, ("evidence", reaction.evidence), "reaction")
                if reaction.evidence in seen:
                    self.r.error(
                        "duplicate-key",
                        "interviews.yaml",
                        key,
                        "two reactions to the same evidence",
                    )
                seen.add(reaction.evidence)
            for t in interview.topics:
                for s in t.statements:
                    if s.claim and s.claim.location:
                        self._ref(
                            "interviews.yaml",
                            f"{person}/{s.key}",
                            ("location", s.claim.location),
                            "claim.location",
                        )
        for ev in b.timeline:
            if ev.location:
                self._ref("timeline.yaml", ev.key, ("location", ev.location), "location")
            for p in ev.people:
                self._ref("timeline.yaml", ev.key, ("person", p), "people")
            self._ref("timeline.yaml", ev.key, ev.source.item, "source")
        for q in b.accusation.questions:
            keys = [o.key for o in q.options or []]
            if len(keys) != len(set(keys)):
                self.r.error(
                    "duplicate-key", "accusation.yaml", q.key, "option keys must be unique"
                )
        if len(self.questions) != len(b.accusation.questions):
            self.r.error("duplicate-key", "accusation.yaml", None, "question keys must be unique")
        for c in b.contradictions:
            file = "spoilers/contradictions.yaml"
            self._ref(file, c.key, ("statement", c.statement), "statement")
            for other in [c.conflicts_with, *c.accept_also]:
                self._ref(file, c.key, other.item, "conflicts_with/accept_also")
                if other.item == ("statement", c.statement):
                    self.r.error("reference", file, c.key, "a statement can't contradict itself")
        for h in b.hints:
            for mention in h.mentions:
                item = parse_ref(mention)
                if item[0] not in ITEM_TYPES:
                    self.r.error(
                        "reference",
                        "spoilers/hints.yaml",
                        h.key,
                        f"mentions: unknown type in {mention!r}",
                    )
                else:
                    self._ref("spoilers/hints.yaml", h.key, item, "mentions")

    def _citations(self, file: str, key: str, refs: list[str], what: str) -> None:
        for ref in refs:
            item = parse_ref(ref)
            if item[0] not in CITABLE_TYPES:
                self.r.error(
                    "reference",
                    file,
                    key,
                    f"{what}: {ref!r} isn't citable (use evidence, statement: or contradiction:)",
                )
            else:
                self._ref(file, key, item, what)

    def _check_solution(self) -> None:
        s, file = self.b.solution, "spoilers/solution.yaml"
        for missing in sorted(set(self.questions) - set(s.answers)):
            self.r.error(
                "reference", file, f"answers.{missing}", "no answer for this accusation question"
            )
        for extra in sorted(set(s.answers) - set(self.questions)):
            self.r.error(
                "reference", file, f"answers.{extra}", "answer for an unknown accusation question"
            )
        for key, spec in s.answers.items():
            q = self.questions.get(key)
            if q is None:
                continue
            where = f"answers.{key}"
            if q.kind == "evidence":
                if spec.correct is not None:
                    self.r.error(
                        "reference", file, where, "evidence questions have no 'correct' value"
                    )
                if spec.proof is None:
                    self.r.error("reference", file, where, "evidence questions need a proof")
            elif spec.correct is None:
                self.r.error("reference", file, where, "'correct' is required")
            elif q.kind == "person" and spec.correct not in self.suspects:
                self.r.error(
                    "reference",
                    file,
                    where,
                    f"correct: {spec.correct!r} isn't a suspect (is_suspect: true)",
                )
            elif q.kind == "choice" and spec.correct not in {o.key for o in q.options or []}:
                self.r.error(
                    "reference", file, where, f"correct: {spec.correct!r} isn't one of the options"
                )
            if spec.proof:
                if q.cite.max == 0:
                    self.r.error(
                        "reference",
                        file,
                        where,
                        "proof is set but the question takes no citations (cite.max is 0)",
                    )
                for group in spec.proof.full + spec.proof.partial:
                    self._citations(file, where, group, "proof")
                    if len(group) > q.cite.max > 0:
                        self.r.error(
                            "reference",
                            file,
                            where,
                            f"proof set {group} needs more citations than cite.max ({q.cite.max})",
                        )
            elif q.cite.min > 0:
                self.r.warning(
                    "reference",
                    file,
                    where,
                    "citations are required but no proof is defined, so they can't score",
                )
        for rh in s.red_herrings:
            if rh.person not in self.suspects:
                self.r.error(
                    "reference", file, f"red_herrings.{rh.person}", "red herring must be a suspect"
                )
            if rh.person in self.culprits:
                self.r.error(
                    "reference",
                    file,
                    f"red_herrings.{rh.person}",
                    "the culprit can't be a red herring",
                )
            self._citations(file, f"red_herrings.{rh.person}", rh.cleared_by, "cleared_by")
        for e in s.key_evidence:
            self._ref(file, "key_evidence", ("evidence", e), "key_evidence")

    def _check_assets(self) -> None:
        b = self.b
        images = [("case.yaml", "cover_image", b.case.cover_image)]
        images += [("people.yaml", p.key, p.portrait) for p in b.people if p.portrait]
        images += [("locations.yaml", loc.key, loc.image) for loc in b.locations if loc.image]
        images += [("evidence.yaml", e.key, e.image) for e in b.evidence if e.image]
        for file, key, rel in images:
            path = (self.folder / rel).resolve()
            if self.folder not in path.parents:
                self.r.error("asset", file, key, f"{rel!r} must stay inside the case folder")
            elif path.suffix.lower() != ".webp":
                self.r.error("asset", file, key, f"{rel!r} must be a .webp image")
            elif not path.is_file():
                self.r.error("asset", file, key, f"{rel!r} doesn't exist")
            else:
                head = path.read_bytes()[:12]
                if head[:4] != WEBP_MAGIC[0] or head[8:12] != WEBP_MAGIC[1]:
                    self.r.error("asset", file, key, f"{rel!r} isn't a valid WebP file")

    def _check_html(self) -> None:
        def strings(value: Any) -> Iterator[str]:
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for v in value.values():
                    yield from strings(v)
            elif isinstance(value, list):
                for v in value:
                    yield from strings(v)

        b = self.b
        groups: list[tuple[str, list[tuple[str | None, Any]]]] = [
            ("case.yaml", [(None, b.case)]),
            ("people.yaml", [(p.key, p) for p in b.people]),
            ("locations.yaml", [(x.key, x) for x in b.locations]),
            ("evidence.yaml", [(e.key, e) for e in b.evidence]),
            ("interviews.yaml", list(b.interviews.items())),
            ("timeline.yaml", [(t.key, t) for t in b.timeline]),
            ("accusation.yaml", [(None, b.accusation)]),
            ("spoilers/contradictions.yaml", [(c.key, c) for c in b.contradictions]),
            ("spoilers/solution.yaml", [(None, b.solution)]),
            ("spoilers/hints.yaml", [(h.key, h) for h in b.hints]),
        ]
        for file, entries in groups:
            for key, model in entries:
                if any(HTML_TAG.search(s) for s in strings(model.model_dump())):
                    self.r.error("html", file, key, "raw HTML isn't allowed; use Markdown")

    def _time(self, value: str | None, file: str, key: str) -> datetime | None:
        if value is None:
            return None
        try:
            return world_time(value, self.b.case.setting.world_date)
        except ValueError:
            self.r.error("timeline", file, key, f"{value!r} isn't HH:MM or YYYY-MM-DDTHH:MM")
            return None

    def _check_timeline(self) -> None:
        world = world_time("00:00", self.b.case.setting.world_date)
        claims: dict[str, tuple[datetime | None, datetime | None, str | None]] = {}
        for person, interview in self.b.interviews.items():
            for t in interview.topics:
                for s in t.statements:
                    if s.claim:
                        ref = f"{person}/{s.key}"
                        start = self._time(s.claim.from_, "interviews.yaml", ref)
                        end = self._time(s.claim.to, "interviews.yaml", ref)
                        if start and end and end < start:
                            self.r.error(
                                "timeline", "interviews.yaml", ref, "claim.to is before claim.from"
                            )
                        claims[ref] = (start, end, s.claim.location)
        for ev in self.b.timeline:
            start = self._time(ev.from_, "timeline.yaml", ev.key)
            end = self._time(ev.to, "timeline.yaml", ev.key)
            if start and end and end < start:
                self.r.error("timeline", "timeline.yaml", ev.key, "'to' is before 'from'")
            if start and abs(start - world) > timedelta(days=30):
                self.r.warning(
                    "timeline", "timeline.yaml", ev.key, "more than 30 days from setting.world_date"
                )
            if ev.source.statement:
                if ev.certainty != "claimed":
                    self.r.error(
                        "timeline",
                        "timeline.yaml",
                        ev.key,
                        "events sourced from a statement must be 'claimed'",
                    )
                claim = claims.get(ev.source.statement)
                if claim:
                    c_start, c_end, c_loc = claim
                    if (c_start, c_end) != (start, end) or (
                        c_loc and ev.location and c_loc != ev.location
                    ):
                        self.r.error(
                            "timeline",
                            "timeline.yaml",
                            ev.key,
                            f"doesn't match the claim in statement {ev.source.statement!r}",
                        )

    # --------------------------------------------------------------------- stage 2: logic

    def logic(self) -> None:
        self.graph = graph = build_graph(self.b)
        self.final = final = simulate(graph)
        self._fairness(graph, final.discovered)
        self._walkthrough(graph)
        self._hints(graph)

    def _fairness(self, graph: CaseGraph, reachable: frozenset[ItemKey]) -> None:
        s, file = self.b.solution, "spoilers/solution.yaml"
        for key, spec in s.answers.items():
            q = self.questions[key]
            if q.kind == "person" and ("person", spec.correct) not in reachable:
                self.r.error(
                    "F1",
                    file,
                    f"answers.{key}",
                    f"the correct answer {spec.correct!r} is never discovered",
                )
            if spec.proof and not any(
                all(parse_ref(r) in reachable for r in group) for group in spec.proof.full
            ):
                self.r.error(
                    "F1", file, f"answers.{key}", "no full proof set can be fully discovered"
                )
        for e in s.key_evidence:
            if ("evidence", e) not in reachable:
                self.r.error("F2", file, "key_evidence", f"key evidence {e!r} is never discovered")
        for rh in s.red_herrings:
            for ref in rh.cleared_by:
                if parse_ref(ref) not in reachable:
                    self.r.error(
                        "F2",
                        file,
                        f"red_herrings.{rh.person}",
                        f"clearing item {ref!r} is never discovered",
                    )
        for item in sorted(set(graph.items) - reachable):
            if item[0] == "contradiction":
                self.r.error(
                    "unreachable-contradiction",
                    "spoilers/contradictions.yaml",
                    item[1],
                    "both sides can never be discovered, so it can't be found",
                )
            else:
                self.r.warning(
                    "F3", _file_for(item[0]), item[1], f"this {item[0]} is never discovered"
                )
        start = discover(graph, frozenset())
        early = set(start)
        for _, loc in [i for i in start if i[0] == "location"]:
            early |= discover(graph, frozenset({("visited", loc)}))
        for culprit in sorted(self.culprits):
            if ("person", culprit) not in early:
                self.r.error(
                    "F4",
                    "people.yaml",
                    culprit,
                    "the culprit must be discoverable at the start or after one visit",
                )
        herrings = {rh.person for rh in s.red_herrings}
        for suspect in sorted(self.suspects - self.culprits - herrings):
            self.r.error(
                "F5", file, "red_herrings", f"suspect {suspect!r} needs a red-herring entry"
            )

    def _walkthrough(self, graph: CaseGraph) -> None:
        file = "spoilers/solution.yaml"
        steps = self.b.solution.walkthrough
        facts: frozenset[tuple[str, str]] = frozenset()

        def fail(index: int, message: str) -> None:
            self.r.error("F6", file, f"walkthrough[{index + 1}]", message)

        for index, step in enumerate(steps):
            found = discover(graph, facts)
            if len(step) != 1:
                fail(index, "each step needs exactly one action")
                return
            ((action, arg),) = step.items()
            if action == "accuse":
                if index != len(steps) - 1:
                    fail(index, "accuse must be the last step")
                    return
                self._accuse(index, arg, found)
                return
            fact = self._step_fact(action, arg, found, graph)
            if isinstance(fact, str):
                fail(index, fact)
                return
            facts = facts | {fact}
        self.r.error("F6", file, "walkthrough", "the walkthrough must end with an accuse step")

    def _step_fact(self, action: str, arg: Any, found: frozenset[ItemKey], graph: CaseGraph):
        need = {"visit": "location", "examine": "evidence", "ask": "topic"}
        if action in need:
            if not isinstance(arg, str) or (need[action], arg) not in found:
                return f"{action}: {arg!r} isn't available yet (not discovered)"
            return ({"visit": "visited", "examine": "examined", "ask": "asked"}[action], arg)
        if action == "present":
            person, _, evidence = str(arg).partition("/")
            if ("person", person) not in found or ("evidence", evidence) not in found:
                return f"present: {arg!r} needs that person and evidence discovered"
            return ("presented", f"{person}/{evidence}")
        if action == "flag":
            if not isinstance(arg, dict) or "statement" not in arg:
                return "flag needs {statement: ..., evidence|statement: ...}"
            other = (
                ("evidence", arg["evidence"])
                if "evidence" in arg
                else ("statement", arg.get("other_statement"))
            )
            statement = ("statement", arg["statement"])
            if statement not in found or other not in found:
                return "flag: both sides must be discovered first"
            key = contradiction_for(graph, arg["statement"], other)
            return (
                ("contradiction", key)
                if key
                else "flag: that pairing isn't an authored contradiction"
            )
        return f"unknown action {action!r} (use visit, examine, ask, present, flag, accuse)"

    def _accuse(self, index: int, arg: Any, found: frozenset[ItemKey]) -> None:
        def fail(message: str) -> None:
            self.r.error("F6", "spoilers/solution.yaml", f"walkthrough[{index + 1}]", message)

        if not isinstance(arg, dict):
            fail("accuse needs a mapping of question → {answer, cite}")
            return
        submission: dict[str, Submission] = {}
        for qkey, answer in arg.items():
            if qkey not in self.questions or not isinstance(answer, dict):
                fail(f"unknown question or bad answer {qkey!r}")
                return
            cites = frozenset(parse_ref(c) for c in answer.get("cite", []))
            hidden = [c for c in cites if c not in found]
            if hidden:
                fail(f"{qkey}: cites items not discovered yet: {sorted(hidden)}")
                return
            submission[qkey] = Submission(answer.get("answer"), cites)
        result = score(*self.scoring_inputs(), submission, self.thresholds())
        if (result.outcome, result.tier) != ("solved", "airtight"):
            fail(
                f"scores {result.score}/{result.max_score} ({result.outcome}, {result.tier}); "
                "it must be solved and airtight"
            )

    def scoring_inputs(self) -> tuple[list[Question], dict[str, AnswerKey]]:
        questions = [
            Question(q.key, q.kind, q.required_for_solve) for q in self.b.accusation.questions
        ]
        key: dict[str, AnswerKey] = {}
        for qkey, spec in self.b.solution.answers.items():
            proof = None
            if spec.proof:
                proof = Proof(
                    spec.proof.points,
                    [{parse_ref(r) for r in g} for g in spec.proof.full],
                    [{parse_ref(r) for r in g} for g in spec.proof.partial],
                )
            key[qkey] = AnswerKey(spec.correct, spec.points, proof)
        return questions, key

    def thresholds(self) -> Thresholds:
        t = self.b.case.rating_thresholds
        return Thresholds(t.airtight, t.convincing) if t else Thresholds()

    def _hints(self, graph: CaseGraph) -> None:
        file = "spoilers/hints.yaml"
        final = self.final
        labels = {
            o.label.lower()
            for key, spec in self.b.solution.answers.items()
            for o in (self.questions[key].options or [])
            if o.key == spec.correct
        }
        terms = {t.lower() for t in self.b.solution.answer_terms} | labels
        covered: set[ItemKey] = set()
        for h in self.b.hints:
            requires = self.conditions[(file, f"{h.key}#requires")]
            resolved = self.conditions[(file, f"{h.key}#resolved_when")]
            covered |= {parse_ref(m) for m in h.mentions}
            covered |= {_atom_item(a) for a in atoms(resolved) if _atom_item(a)}
            if not evaluate(requires, final.facts, final.discovered):
                self.r.error(
                    "F12", file, h.key, "requires can never be met, so the track is never offered"
                )
                continue
            if not evaluate(resolved, final.facts, final.discovered):
                self.r.error(
                    "F12",
                    file,
                    h.key,
                    "resolved_when can never be met, so the track never resolves",
                )
            avoiding = reachable_without(graph, resolved)
            if not evaluate(requires, avoiding.facts, avoiding.discovered):
                self.r.error(
                    "F12", file, h.key, "the track only becomes relevant once it's already resolved"
                )
            safe = guaranteed(graph, requires)
            for mention in h.mentions:
                if parse_ref(mention) not in safe:
                    self.r.error(
                        "F12",
                        file,
                        h.key,
                        f"mentions {mention!r}, but it isn't guaranteed to be discovered "
                        "when the track is offered",
                    )
            for tier in h.tiers:
                text = tier.text.lower()
                hits = sorted(t for t in terms if t in text)
                if hits:
                    self.r.warning(
                        "F14",
                        file,
                        f"{h.key}.{tier.level}",
                        f"tier text contains answer terms {hits}",
                    )
        needed: set[ItemKey] = set()
        key_evidence = {("evidence", e) for e in self.b.solution.key_evidence}
        for spec in self.b.solution.answers.values():
            for group in spec.proof.full if spec.proof else []:
                for item in map(parse_ref, group):
                    if item[0] == "contradiction" or item in key_evidence:
                        needed.add(item)
        for item in sorted(needed - covered):
            self.r.warning(
                "F13",
                file,
                None,
                f"no hint track covers {item[0]} {item[1]!r} (add it to resolved_when or mentions)",
            )


def _atom_item(atom: object) -> ItemKey | None:
    if isinstance(atom, Discovered):
        return (atom.type, atom.ref)
    if isinstance(atom, Fact) and atom.kind in FACT_TARGET:
        return (FACT_TARGET[atom.kind], atom.ref)
    return None


def _file_for(item_type: str) -> str:
    return {
        "person": "people.yaml",
        "location": "locations.yaml",
        "evidence": "evidence.yaml",
        "topic": "interviews.yaml",
        "statement": "interviews.yaml",
        "timeline_event": "timeline.yaml",
        "contradiction": "spoilers/contradictions.yaml",
    }[item_type]


def to_mermaid(graph: CaseGraph | None) -> str:
    """Unlock graph as Mermaid text: an edge A → B means B's condition refers to A."""
    if graph is None:
        return ""

    def node(item: ItemKey) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", f"{item[0]}__{item[1]}")

    lines = ["graph LR"]
    for item in sorted(graph.items):
        lines.append(f'  {node(item)}["{item[0]}: {item[1]}"]')
    edges: set[tuple[str, str]] = set()
    for item, cond in graph.items.items():
        for atom in atoms(cond):
            source = _atom_item(atom)
            if isinstance(atom, Fact) and atom.kind == "presented":
                source = ("evidence", atom.ref.partition("/")[2])
            if source and source != item and source in graph.items:
                edges.add((node(source), node(item)))
    for spec in graph.contradictions.values():
        target = node(("contradiction", spec.key))
        edges.add((node(("statement", spec.statement)), target))
        edges.update((node(c), target) for c in spec.conflicts if c in graph.items)
    lines += [f"  {a} --> {b}" for a, b in sorted(edges)]
    return "\n".join(lines) + "\n"
