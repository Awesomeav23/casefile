"""Pure discovery-engine core (docs/ARCHITECTURE.md §3.2).

Given a case's compiled graph (each item's *effective* unlock condition) and a player's
facts, it computes what the player has discovered. The validator uses the same functions to
prove a case solvable. M7 adds a persistence wrapper (Fact/Discovery rows) around this core.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .conditions import Condition, Discovered, Fact, FactKey, ItemKey, dnf, evaluate


@dataclass(frozen=True)
class ContradictionSpec:
    key: str
    statement: str  # "<person>/<statement>"
    conflicts: frozenset[ItemKey]  # the authored conflicting item plus any accept_also items


@dataclass(frozen=True)
class CaseGraph:
    items: Mapping[ItemKey, Condition]
    contradictions: Mapping[str, ContradictionSpec]


@dataclass(frozen=True)
class State:
    facts: frozenset[FactKey]
    discovered: frozenset[ItemKey]


def discover(
    graph: CaseGraph, facts: frozenset[FactKey], seed: Iterable[ItemKey] = ()
) -> frozenset[ItemKey]:
    """Fixpoint of every item whose condition holds (`discovered:` atoms can chain)."""
    found = set(seed)
    changed = True
    while changed:
        changed = False
        snapshot = frozenset(found)
        for item, cond in graph.items.items():
            if item not in found and evaluate(cond, facts, snapshot):
                found.add(item)
                changed = True
    return frozenset(found)


def contradiction_for(graph: CaseGraph, statement: str, conflict: ItemKey) -> str | None:
    """The authored contradiction a (statement, conflicting item) pairing confirms, if any."""
    for spec in graph.contradictions.values():
        if spec.statement == statement and conflict in spec.conflicts:
            return spec.key
        if conflict == ("statement", spec.statement) and ("statement", statement) in spec.conflicts:
            return spec.key  # statement-vs-statement flagged in the other order
    return None


def available_facts(graph: CaseGraph, discovered: frozenset[ItemKey]) -> frozenset[FactKey]:
    """Every fact a player could create next by one action."""
    people = [ref for t, ref in discovered if t == "person"]
    evidence = [ref for t, ref in discovered if t == "evidence"]
    facts: set[FactKey] = set()
    for item_type, ref in discovered:
        if item_type == "location":
            facts.add(("visited", ref))
        elif item_type == "evidence":
            facts.add(("examined", ref))
        elif item_type == "topic":
            facts.add(("asked", ref))
    facts.update(("presented", f"{p}/{e}") for p in people for e in evidence)
    for spec in graph.contradictions.values():
        if ("statement", spec.statement) in discovered and spec.conflicts & discovered:
            facts.add(("contradiction", spec.key))
    return frozenset(facts)


def simulate(graph: CaseGraph) -> State:
    """Take every available action until nothing new appears (terminates: monotonic, finite)."""
    facts: frozenset[FactKey] = frozenset()
    while True:
        found = discover(graph, facts)
        new = available_facts(graph, found) - facts
        if not new:
            return State(facts, found)
        facts = facts | new


def implied_items(graph: CaseGraph, facts: Iterable[FactKey]) -> set[ItemKey]:
    """Items a fact proves were already discovered (you can only act on what you've found)."""
    items: set[ItemKey] = set()
    for kind, ref in facts:
        if kind == "visited":
            items.add(("location", ref))
        elif kind == "examined":
            items.add(("evidence", ref))
        elif kind == "asked":
            items.update({("person", ref.split("/")[0]), ("topic", ref)})
        elif kind == "presented":
            person, _, evidence = ref.partition("/")
            items.update({("person", person), ("evidence", evidence)})
        elif kind == "contradiction" and ref in graph.contradictions:
            spec = graph.contradictions[ref]
            items.update({("contradiction", ref), ("statement", spec.statement)})
            if len(spec.conflicts) == 1:  # with alternatives we can't know which side was used
                items.update(spec.conflicts)
    return items


def guaranteed(graph: CaseGraph, cond: Condition) -> frozenset[ItemKey]:
    """Items discovered in *every* minimal situation where `cond` holds."""
    result: frozenset[ItemKey] | None = None
    for clause in dnf(cond):
        facts = frozenset((a.kind, a.ref) for a in clause if isinstance(a, Fact))
        seed = {(a.type, a.ref) for a in clause if isinstance(a, Discovered)}
        found = discover(graph, facts, seed | implied_items(graph, facts))
        result = found if result is None else result & found
    return result or frozenset()


def reachable_without(graph: CaseGraph, cond: Condition) -> State:
    """A maximal reachable state in which `cond` is still false (greedy, one fact at a time)."""
    facts: frozenset[FactKey] = frozenset()
    progressed = True
    while progressed:
        progressed = False
        for fact in sorted(available_facts(graph, discover(graph, facts)) - facts):
            trial = facts | {fact}
            if not evaluate(cond, trial, discover(graph, trial)):
                facts = trial
                progressed = True
    return State(facts, discover(graph, facts))
