"""Pure accusation scoring (docs/CASE_DESIGN.md §5.9, docs/PRODUCT_SPEC.md §6).

Per question: answer points if correct, plus proof points if the citations contain a `full`
proof set (half, rounded down, for a `partial` set). Proof only counts when the answer is
correct. An `evidence`-kind question has no answer: it is correct when a full set is cited.
Hint use and elapsed time don't affect the score (D-21, D-15 defaults).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .conditions import ItemKey


@dataclass(frozen=True)
class Question:
    key: str
    kind: str  # person | choice | evidence
    required_for_solve: bool = False


@dataclass(frozen=True)
class Proof:
    points: int
    full: list[set[ItemKey]]
    partial: list[set[ItemKey]] = field(default_factory=list)


@dataclass(frozen=True)
class AnswerKey:
    correct: str | None
    points: int = 0
    proof: Proof | None = None


@dataclass(frozen=True)
class Submission:
    answer: str | None
    cite: frozenset[ItemKey] = frozenset()


@dataclass(frozen=True)
class Thresholds:
    airtight: float = 0.9
    convincing: float = 0.7


@dataclass(frozen=True)
class QuestionResult:
    key: str
    correct: bool
    answer_points: int
    proof_points: int
    max_points: int

    @property
    def earned(self) -> int:
        return self.answer_points + self.proof_points


@dataclass(frozen=True)
class ScoreResult:
    score: int
    max_score: int
    outcome: str  # solved | unsolved
    tier: str | None  # airtight | convincing | shaky, or None when unsolved
    breakdown: tuple[QuestionResult, ...]

    def question(self, key: str) -> QuestionResult:
        return next(q for q in self.breakdown if q.key == key)


def _contains_any(cited: frozenset[ItemKey], sets: Iterable[set[ItemKey]]) -> bool:
    return any(s <= cited for s in sets)


def _proof_points(proof: Proof | None, cited: frozenset[ItemKey]) -> int:
    if proof is None:
        return 0
    if _contains_any(cited, proof.full):
        return proof.points
    if _contains_any(cited, proof.partial):
        return proof.points // 2
    return 0


def score_question(question: Question, key: AnswerKey, sub: Submission | None) -> QuestionResult:
    sub = sub or Submission(None)
    proof_max = key.proof.points if key.proof else 0
    if question.kind == "evidence":
        correct = key.proof is not None and _contains_any(sub.cite, key.proof.full)
        answer_points = 0
    else:
        correct = sub.answer is not None and sub.answer == key.correct
        answer_points = key.points if correct else 0
    proof_points = (
        _proof_points(key.proof, sub.cite) if (correct or question.kind == "evidence") else 0
    )
    return QuestionResult(
        question.key, correct, answer_points, proof_points, key.points + proof_max
    )


def score(
    questions: Iterable[Question],
    answer_key: Mapping[str, AnswerKey],
    submission: Mapping[str, Submission],
    thresholds: Thresholds,
) -> ScoreResult:
    questions = list(questions)
    breakdown = tuple(
        score_question(q, answer_key[q.key], submission.get(q.key)) for q in questions
    )
    total = sum(r.earned for r in breakdown)
    maximum = sum(r.max_points for r in breakdown)
    solved = all(
        r.correct for q, r in zip(questions, breakdown, strict=True) if q.required_for_solve
    )
    if not solved:
        return ScoreResult(total, maximum, "unsolved", None, breakdown)
    ratio = total / maximum if maximum else 1.0
    tier = (
        "airtight"
        if ratio >= thresholds.airtight
        else "convincing"
        if ratio >= thresholds.convincing
        else "shaky"
    )
    return ScoreResult(total, maximum, "solved", tier, breakdown)
