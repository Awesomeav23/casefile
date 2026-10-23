"""Pure scoring (CASE_DESIGN §5.9, PRODUCT_SPEC §6; TESTING_PLAN §2.4)."""

import pytest

from play.scoring import AnswerKey, Proof, Question, Submission, Thresholds, score

E = lambda key: ("evidence", key)  # noqa: E731

QUESTIONS = [
    Question("culprit", "person", required_for_solve=True),
    Question("method", "choice"),
    Question("where", "evidence"),
]
KEY = {
    "culprit": AnswerKey("ada", points=40),
    "method": AnswerKey(
        "override",
        points=20,
        proof=Proof(points=20, full=[{E("log")}, {E("email"), E("gap")}], partial=[{E("gap")}]),
    ),
    "where": AnswerKey(None, points=0, proof=Proof(points=20, full=[{E("crate")}])),
}
DEFAULT = Thresholds()


def run(culprit="ada", method="override", method_cite=(), where_cite=(), thresholds=DEFAULT):
    return score(
        QUESTIONS,
        KEY,
        {
            "culprit": Submission(culprit),
            "method": Submission(method, frozenset(method_cite)),
            "where": Submission(None, frozenset(where_cite)),
        },
        thresholds,
    )


def test_full_marks_are_airtight():
    result = run(method_cite=[E("log")], where_cite=[E("crate")])
    assert (result.score, result.max_score) == (100, 100)
    assert (result.outcome, result.tier) == ("solved", "airtight")


def test_partial_proof_earns_half_rounded_down():
    result = run(method_cite=[E("gap")], where_cite=[E("crate")])
    method = result.question("method")
    assert (method.answer_points, method.proof_points) == (20, 10)


def test_correct_answer_without_proof_earns_answer_points_only():
    method = run(method_cite=[E("other")]).question("method")
    assert (method.correct, method.answer_points, method.proof_points) == (True, 20, 0)


def test_wrong_answer_earns_no_proof_points_even_with_correct_citations():
    method = run(method="guard", method_cite=[E("log")]).question("method")
    assert (method.correct, method.answer_points, method.proof_points) == (False, 0, 0)


def test_superset_of_a_full_set_counts():
    proof = run(method_cite=[E("email"), E("gap"), E("noise")]).question("method").proof_points
    assert proof == 20


def test_evidence_question_scores_on_proof_only():
    where = run(where_cite=[E("crate")]).question("where")
    assert (where.correct, where.proof_points) == (True, 20)
    assert run(where_cite=[E("nope")]).question("where").correct is False


def test_wrong_required_answer_is_unsolved_regardless_of_score():
    result = run(culprit="ben", method_cite=[E("log")], where_cite=[E("crate")])
    assert (result.outcome, result.tier) == ("unsolved", None)
    assert result.score == 60


@pytest.mark.parametrize(
    "method_cite, where_cite, tier",
    [
        ([E("log")], [E("crate")], "airtight"),  # 100%
        ([E("gap")], [E("crate")], "airtight"),  # 90% (boundary counts)
        ([], [E("crate")], "convincing"),  # 80%
        ([E("log")], [], "convincing"),  # 80%
        ([E("gap")], [], "convincing"),  # 70% (boundary counts)
        ([], [], "shaky"),  # 60%
    ],
)
def test_tier_thresholds(method_cite, where_cite, tier):
    assert run(method_cite=method_cite, where_cite=where_cite).tier == tier


def test_case_can_override_thresholds():
    strict = Thresholds(airtight=0.95, convincing=0.85)
    assert run(method_cite=[E("gap")], where_cite=[E("crate")], thresholds=strict).tier == (
        "convincing"
    )


def test_missing_answer_is_treated_as_wrong():
    result = score(QUESTIONS, KEY, {"method": Submission("override")}, DEFAULT)
    assert result.question("culprit").correct is False
    assert result.outcome == "unsolved"
