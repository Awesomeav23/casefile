"""Unlock-condition language (CASE_DESIGN §4; TESTING_PLAN §2.1)."""

import itertools

import pytest

from play.conditions import (
    AllOf,
    AnyOf,
    ConditionError,
    Discovered,
    Fact,
    Start,
    all_of,
    atoms,
    dnf,
    evaluate,
    parse,
    to_json,
)


def ev(raw, facts=(), discovered=()):
    return evaluate(parse(raw), frozenset(facts), frozenset(discovered))


class TestParse:
    def test_start(self):
        assert parse("start") == Start()

    @pytest.mark.parametrize("kind", ["visited", "examined", "asked", "presented", "contradiction"])
    def test_fact_atoms(self, kind):
        assert parse({kind: "x/y"}) == Fact(kind, "x/y")

    def test_discovered(self):
        assert parse({"discovered": "statement:ada/at-market"}) == Discovered(
            "statement", "ada/at-market"
        )

    def test_nested(self):
        cond = parse({"all": [{"visited": "shed"}, {"any": [{"asked": "a/b"}, "start"]}]})
        assert cond == AllOf((Fact("visited", "shed"), AnyOf((Fact("asked", "a/b"), Start()))))

    @pytest.mark.parametrize(
        "raw, fragment",
        [
            ({"all": []}, "at least one"),
            ({"any": []}, "at least one"),
            ({"all": "start"}, "must be a list"),
            ({"not": {"visited": "x"}}, "Unknown condition"),
            ({"visited": ""}, "non-empty"),
            ({"visited": 3}, "non-empty"),
            ({"visited": "a", "examined": "b"}, "exactly one key"),
            ({"discovered": "nope"}, "type:ref"),
            ({"discovered": "planet:mars"}, "Unknown item type"),
            ("begin", "Unknown condition"),
            (None, "Unknown condition"),
            ([], "Unknown condition"),
        ],
    )
    def test_rejects_invalid(self, raw, fragment):
        with pytest.raises(ConditionError, match=fragment):
            parse(raw)


class TestEvaluate:
    def test_start_is_true(self):
        assert ev("start")

    def test_fact_true_and_false(self):
        assert ev({"visited": "shed"}, facts=[("visited", "shed")])
        assert not ev({"visited": "shed"}, facts=[("visited", "kitchen")])
        assert not ev({"visited": "shed"}, facts=[("examined", "shed")])

    def test_discovered(self):
        assert ev({"discovered": "evidence:ticket"}, discovered=[("evidence", "ticket")])
        assert not ev({"discovered": "evidence:ticket"}, discovered=[("location", "ticket")])

    def test_all_and_any(self):
        raw = {"all": [{"visited": "a"}, {"any": [{"examined": "x"}, {"examined": "y"}]}]}
        assert not ev(raw, facts=[("visited", "a")])
        assert ev(raw, facts=[("visited", "a"), ("examined", "y")])
        assert not ev(raw, facts=[("examined", "x"), ("examined", "y")])

    def test_monotonic(self):
        """Adding facts never turns a true condition false (no negation exists)."""
        raw = {"all": [{"visited": "a"}, {"any": [{"examined": "x"}, {"asked": "p/t"}]}]}
        universe = [("visited", "a"), ("examined", "x"), ("asked", "p/t"), ("visited", "b")]
        cond = parse(raw)
        for size in range(len(universe) + 1):
            for subset in itertools.combinations(universe, size):
                if evaluate(cond, frozenset(subset), frozenset()):
                    for extra in universe:
                        assert evaluate(cond, frozenset({*subset, extra}), frozenset())


class TestHelpers:
    def test_atoms_walks_the_tree(self):
        cond = parse({"all": [{"visited": "a"}, {"any": [{"discovered": "evidence:x"}, "start"]}]})
        assert set(atoms(cond)) == {Fact("visited", "a"), Discovered("evidence", "x"), Start()}

    def test_to_json_round_trips(self):
        raw = {"all": [{"visited": "a"}, {"any": [{"discovered": "evidence:x"}, "start"]}]}
        assert to_json(parse(raw)) == raw
        assert parse(to_json(parse(raw))) == parse(raw)

    def test_all_of_combines_and_drops_start(self):
        assert all_of() == Start()
        assert all_of(Start(), Fact("visited", "a")) == Fact("visited", "a")
        assert all_of(Fact("visited", "a"), Fact("asked", "p/t")) == AllOf(
            (Fact("visited", "a"), Fact("asked", "p/t"))
        )

    def test_dnf(self):
        cond = parse({"all": [{"visited": "a"}, {"any": [{"examined": "x"}, {"examined": "y"}]}]})
        assert set(dnf(cond)) == {
            frozenset({Fact("visited", "a"), Fact("examined", "x")}),
            frozenset({Fact("visited", "a"), Fact("examined", "y")}),
        }
        assert dnf(Start()) == [frozenset()]
