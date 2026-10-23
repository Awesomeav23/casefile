"""Pure discovery engine (ARCHITECTURE §3.2; TESTING_PLAN §2.2)."""

from play.conditions import AllOf, parse
from play.engine import (
    CaseGraph,
    ContradictionSpec,
    available_facts,
    contradiction_for,
    discover,
    guaranteed,
    reachable_without,
    simulate,
)

# A hand-built graph shaped like the compiler's output (content/compile.py):
#   person ada, ben (start) · location shed, kitchen (start)
#   evidence rack @shed · ticket @kitchen · quote @kitchen + asked ben/bike
#   · pass (asked ben/morning)
#   topics ada/morning, ben/morning, ben/bike (need their person) · confront (needs contradiction)
#   statements by topic or reaction · timeline needs its source · contradiction c1
D = parse
GRAPH = CaseGraph(
    items={
        ("person", "ada"): D("start"),
        ("person", "ben"): D("start"),
        ("location", "shed"): D("start"),
        ("location", "kitchen"): D("start"),
        ("evidence", "rack"): D({"visited": "shed"}),
        ("evidence", "ticket"): D({"visited": "kitchen"}),
        ("evidence", "quote"): D({"all": [{"visited": "kitchen"}, {"asked": "ben/bike"}]}),
        ("evidence", "pass"): D({"asked": "ben/morning"}),
        ("topic", "ada/morning"): D({"discovered": "person:ada"}),
        ("topic", "ben/morning"): D({"discovered": "person:ben"}),
        ("topic", "ben/bike"): D({"discovered": "person:ben"}),
        ("topic", "ada/confront"): AllOf(
            (D({"discovered": "person:ada"}), D({"contradiction": "c1"}))
        ),
        ("statement", "ada/at-market"): D({"asked": "ada/morning"}),
        ("statement", "ada/ticket-reaction"): D({"presented": "ada/ticket"}),
        ("statement", "ada/admits"): D({"asked": "ada/confront"}),
        ("statement", "ben/bike-broke"): D({"asked": "ben/bike"}),
        ("timeline_event", "ticket-stamp"): D(
            {"all": [{"discovered": "evidence:ticket"}, {"examined": "ticket"}]}
        ),
        ("contradiction", "c1"): D({"contradiction": "c1"}),
    },
    contradictions={
        "c1": ContradictionSpec(
            "c1", "ada/at-market", frozenset({("evidence", "ticket"), ("evidence", "rack")})
        )
    },
)


def test_initial_discovery_is_start_items_and_dependent_topics():
    found = discover(GRAPH, frozenset())
    assert found == {
        ("person", "ada"),
        ("person", "ben"),
        ("location", "shed"),
        ("location", "kitchen"),
        ("topic", "ada/morning"),
        ("topic", "ben/morning"),
        ("topic", "ben/bike"),
    }


def test_evidence_with_location_needs_a_visit():
    assert ("evidence", "ticket") not in discover(GRAPH, frozenset())
    assert ("evidence", "ticket") in discover(GRAPH, frozenset({("visited", "kitchen")}))


def test_implicit_visit_is_combined_with_explicit_requires():
    assert ("evidence", "quote") not in discover(GRAPH, frozenset({("visited", "kitchen")}))
    assert ("evidence", "quote") not in discover(GRAPH, frozenset({("asked", "ben/bike")}))
    both = frozenset({("visited", "kitchen"), ("asked", "ben/bike")})
    assert ("evidence", "quote") in discover(GRAPH, both)


def test_chains_resolve_in_one_call():
    found = discover(GRAPH, frozenset({("contradiction", "c1"), ("asked", "ada/confront")}))
    assert {
        ("contradiction", "c1"),
        ("topic", "ada/confront"),
        ("statement", "ada/admits"),
    } <= found


def test_discover_is_idempotent_and_honours_seed():
    facts = frozenset({("visited", "kitchen")})
    assert discover(GRAPH, facts) == discover(GRAPH, facts)
    assert ("evidence", "pass") in discover(GRAPH, frozenset(), seed={("evidence", "pass")})


def test_statements_need_their_trigger():
    assert ("statement", "ada/at-market") in discover(GRAPH, frozenset({("asked", "ada/morning")}))
    reaction = discover(GRAPH, frozenset({("presented", "ada/ticket")}))
    assert ("statement", "ada/ticket-reaction") in reaction


def test_timeline_event_needs_its_source_discovered():
    assert ("timeline_event", "ticket-stamp") not in discover(
        GRAPH, frozenset({("examined", "ticket")})
    )
    facts = frozenset({("visited", "kitchen"), ("examined", "ticket")})
    assert ("timeline_event", "ticket-stamp") in discover(GRAPH, facts)


def test_available_facts():
    found = discover(GRAPH, frozenset({("visited", "kitchen"), ("asked", "ada/morning")}))
    facts = available_facts(GRAPH, found)
    assert ("visited", "shed") in facts
    assert ("examined", "ticket") in facts
    assert ("asked", "ben/bike") in facts
    assert ("presented", "ben/ticket") in facts
    assert ("contradiction", "c1") in facts  # statement + an accepted conflict are discovered
    assert ("examined", "quote") not in facts  # not discovered yet


def test_contradiction_for_accepts_any_listed_conflict():
    assert contradiction_for(GRAPH, "ada/at-market", ("evidence", "rack")) == "c1"
    assert contradiction_for(GRAPH, "ada/at-market", ("evidence", "pass")) is None


def test_simulate_reaches_everything_reachable():
    state = simulate(GRAPH)
    assert state.discovered == frozenset(GRAPH.items)


def test_guaranteed_items_for_a_condition():
    cond = parse({"all": [{"visited": "kitchen"}, {"asked": "ben/bike"}]})
    assert {("evidence", "quote"), ("evidence", "ticket")} <= guaranteed(GRAPH, cond)
    either = parse({"any": [{"visited": "kitchen"}, {"visited": "shed"}]})
    assert ("evidence", "ticket") not in guaranteed(GRAPH, either)


def test_reachable_without_keeps_the_condition_false():
    state = reachable_without(GRAPH, parse({"contradiction": "c1"}))
    assert ("contradiction", "c1") not in state.facts
    assert ("statement", "ada/at-market") in state.discovered  # everything else still reachable
    assert ("evidence", "quote") in state.discovered
