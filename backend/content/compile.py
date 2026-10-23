"""Compile a CaseBundle into the engine's CaseGraph (each item's *effective* condition).

Implicit rules from docs/CASE_DESIGN.md §4:
- people and locations default to `start`;
- evidence with a location also needs `visited: <location>`;
- topics also need their person discovered;
- statements are revealed by their topic (`asked`) or reaction (`presented`);
- timeline events also need their source discovered (so they never cite hidden items);
- a contradiction item is discovered when it is confirmed (`contradiction: <key>`).
Assumes the bundle passed the validator's condition and reference checks.
"""

from __future__ import annotations

from play.conditions import Condition, Discovered, Fact, ItemKey, Start, all_of, parse
from play.engine import CaseGraph, ContradictionSpec

from .schema import CaseBundle, OneRef

CITABLE_TYPES = ("evidence", "statement", "contradiction")


def parse_ref(ref: str, default_type: str = "evidence") -> ItemKey:
    """Citation shorthand: `alarm-log` → evidence; `statement:a/b`, `contradiction:k`, …"""
    item_type, sep, rest = ref.partition(":")
    return (item_type, rest) if sep else (default_type, ref)


def side(ref: OneRef) -> ItemKey:
    return ref.item


def _optional(raw: object) -> Condition:
    return Start() if raw is None else parse(raw)


def build_graph(bundle: CaseBundle) -> CaseGraph:
    items: dict[ItemKey, Condition] = {}

    for person in bundle.people:
        items[("person", person.key)] = _optional(person.requires)
    for location in bundle.locations:
        items[("location", location.key)] = _optional(location.requires)
    for evidence in bundle.evidence:
        visit = Fact("visited", evidence.location) if evidence.location else Start()
        items[("evidence", evidence.key)] = all_of(visit, _optional(evidence.requires))

    for person_key, interview in bundle.interviews.items():
        for topic in interview.topics:
            ref = f"{person_key}/{topic.key}"
            items[("topic", ref)] = all_of(
                Discovered("person", person_key), _optional(topic.requires)
            )
            for statement in topic.statements:
                items[("statement", f"{person_key}/{statement.key}")] = Fact("asked", ref)
        for reaction in interview.reactions:
            trigger = Fact("presented", f"{person_key}/{reaction.evidence}")
            for statement in reaction.statements:
                items[("statement", f"{person_key}/{statement.key}")] = trigger

    for event in bundle.timeline:
        source_type, source_ref = side(event.source)
        items[("timeline_event", event.key)] = all_of(
            Discovered(source_type, source_ref), parse(event.requires)
        )

    contradictions: dict[str, ContradictionSpec] = {}
    for entry in bundle.contradictions:
        items[("contradiction", entry.key)] = Fact("contradiction", entry.key)
        conflicts = frozenset({side(entry.conflicts_with), *(side(a) for a in entry.accept_also)})
        contradictions[entry.key] = ContradictionSpec(entry.key, entry.statement, conflicts)

    return CaseGraph(items=items, contradictions=contradictions)
