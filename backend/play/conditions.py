"""The unlock-condition language (docs/CASE_DESIGN.md §4).

Pure Python: no Django, no database. Conditions are monotonic (no negation, counters or
randomness), so adding facts can never make a true condition false. The validator relies
on that to prove solvability by exhaustive simulation.

YAML forms accepted by `parse`:
    start
    {visited: <location>}       {examined: <evidence>}      {asked: <person>/<topic>}
    {presented: <person>/<evidence>}                         {contradiction: <key>}
    {discovered: <type>:<ref>}
    {all: [<condition>, ...]}   {any: [<condition>, ...]}    (non-empty lists)
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import product

FACT_KINDS = ("visited", "examined", "asked", "presented", "contradiction")
ITEM_TYPES = (
    "person",
    "location",
    "evidence",
    "topic",
    "statement",
    "timeline_event",
    "contradiction",
)

FactKey = tuple[str, str]  # (kind, ref), e.g. ("asked", "corinne-blake/her-talk")
ItemKey = tuple[str, str]  # (type, ref), e.g. ("evidence", "alarm-log")


class ConditionError(ValueError):
    """An authored condition doesn't match the language."""


@dataclass(frozen=True)
class Start:
    pass


@dataclass(frozen=True)
class Fact:
    kind: str
    ref: str


@dataclass(frozen=True)
class Discovered:
    type: str
    ref: str


@dataclass(frozen=True)
class AllOf:
    terms: tuple[Condition, ...]


@dataclass(frozen=True)
class AnyOf:
    terms: tuple[Condition, ...]


Condition = Start | Fact | Discovered | AllOf | AnyOf
Atom = Start | Fact | Discovered


def parse(raw: object) -> Condition:
    if raw == "start":
        return Start()
    if not isinstance(raw, dict):
        raise ConditionError(f"Unknown condition {raw!r}. Use 'start' or a one-key mapping.")
    if len(raw) != 1:
        raise ConditionError(f"A condition must have exactly one key, got {sorted(raw)}.")
    ((key, value),) = raw.items()

    if key in ("all", "any"):
        if not isinstance(value, list):
            raise ConditionError(f"'{key}' must be a list of conditions.")
        if not value:
            raise ConditionError(f"'{key}' needs at least one condition.")
        terms = tuple(parse(term) for term in value)
        return AllOf(terms) if key == "all" else AnyOf(terms)

    if key in FACT_KINDS or key == "discovered":
        if not isinstance(value, str) or not value.strip():
            raise ConditionError(f"'{key}' needs a non-empty reference string.")
        if key != "discovered":
            return Fact(key, value)
        item_type, sep, ref = value.partition(":")
        if not sep or not ref:
            raise ConditionError(f"'discovered' needs 'type:ref', got {value!r}.")
        if item_type not in ITEM_TYPES:
            raise ConditionError(
                f"Unknown item type {item_type!r} in 'discovered'. Use one of {list(ITEM_TYPES)}."
            )
        return Discovered(item_type, ref)

    raise ConditionError(
        f"Unknown condition {key!r}. Use start, all, any, discovered, or one of {list(FACT_KINDS)}."
    )


def evaluate(cond: Condition, facts: frozenset[FactKey], discovered: frozenset[ItemKey]) -> bool:
    match cond:
        case Start():
            return True
        case Fact(kind, ref):
            return (kind, ref) in facts
        case Discovered(item_type, ref):
            return (item_type, ref) in discovered
        case AllOf(terms):
            return all(evaluate(t, facts, discovered) for t in terms)
        case AnyOf(terms):
            return any(evaluate(t, facts, discovered) for t in terms)
    raise TypeError(f"Not a condition: {cond!r}")


def atoms(cond: Condition) -> Iterator[Atom]:
    if isinstance(cond, AllOf | AnyOf):
        for term in cond.terms:
            yield from atoms(term)
    else:
        yield cond


def all_of(*conds: Condition) -> Condition:
    """Conjunction that drops `start` and flattens trivial cases."""
    terms = tuple(c for c in conds if not isinstance(c, Start))
    if not terms:
        return Start()
    return terms[0] if len(terms) == 1 else AllOf(terms)


def dnf(cond: Condition) -> list[frozenset[Atom]]:
    """Disjunctive normal form: each set is one minimal way to satisfy the condition."""
    match cond:
        case Start():
            return [frozenset()]
        case Fact() | Discovered():
            return [frozenset({cond})]
        case AnyOf(terms):
            return [clause for t in terms for clause in dnf(t)]
        case AllOf(terms):
            return [frozenset().union(*combo) for combo in product(*(dnf(t) for t in terms))]
    raise TypeError(f"Not a condition: {cond!r}")


def to_json(cond: Condition) -> object:
    """Normalised JSON form, stored in the database (DATA_MODEL `requires` columns)."""
    match cond:
        case Start():
            return "start"
        case Fact(kind, ref):
            return {kind: ref}
        case Discovered(item_type, ref):
            return {"discovered": f"{item_type}:{ref}"}
        case AllOf(terms):
            return {"all": [to_json(t) for t in terms]}
        case AnyOf(terms):
            return {"any": [to_json(t) for t in terms]}
    raise TypeError(f"Not a condition: {cond!r}")


def fact_atoms(conds: Iterable[Condition]) -> set[Fact]:
    return {a for c in conds for a in atoms(c) if isinstance(a, Fact)}
