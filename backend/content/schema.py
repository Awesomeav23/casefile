"""Case authoring format v1: one Pydantic model per YAML file (docs/CASE_DESIGN.md §5).

These models check shape, types, enums, and required fields. Cross-file rules (references,
reachability, fairness) live in validator.py. Conditions (`requires`, `resolved_when`) are
kept raw here and parsed by play.conditions, so their errors can name the exact item.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

FORMAT_VERSION = 1

KEY_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
Key = Annotated[str, StringConstraints(pattern=KEY_PATTERN, max_length=80)]
Text = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
Ref = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
RawCondition = Any  # validated by play.conditions.parse


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- case.yaml ---------------------------------------------------------------------------


class Setting(Model):
    world_date: dt.date
    era_note: str | None = None


class RatingThresholds(Model):
    airtight: float = Field(gt=0, le=1)
    convincing: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.convincing >= self.airtight:
            raise ValueError("convincing must be lower than airtight")
        return self


class CaseFile(Model):
    format_version: Literal[1]
    slug: Key
    title: Text
    tagline: Text
    difficulty: Literal["introductory", "standard", "hard"]
    estimated_minutes: int = Field(gt=0, le=600)
    tags: list[Key] = []
    content_notes: list[Text] = []
    setting: Setting
    copyright: Text
    cover_image: Text
    cover_alt: Text
    briefing: Text
    objective: Text
    rating_thresholds: RatingThresholds | None = None


# --- people.yaml / locations.yaml / evidence.yaml -----------------------------------------


def _alt_required(image: str | None, alt: str | None, field: str) -> None:
    if image and not (alt and alt.strip()):
        raise ValueError(f"{field}_alt is required when {field} is set")


class Person(Model):
    key: Key
    name: Text
    role: Text
    is_suspect: bool
    summary: Text
    bio: str | None = None
    default_reaction: Text
    portrait: str | None = None
    portrait_alt: str | None = None
    requires: RawCondition = None

    @model_validator(mode="after")
    def alt(self):
        _alt_required(self.portrait, self.portrait_alt, "portrait")
        return self


class Location(Model):
    key: Key
    name: Text
    description: Text
    image: str | None = None
    image_alt: str | None = None
    requires: RawCondition = None

    @model_validator(mode="after")
    def alt(self):
        _alt_required(self.image, self.image_alt, "image")
        return self


EvidenceKind = Literal["document", "photo", "object", "record", "correspondence", "transcript"]


class Evidence(Model):
    key: Key
    title: Text
    kind: EvidenceKind
    summary: Text
    body: Text
    location: Key | None = None
    people: list[Key] = []
    image: str | None = None
    image_alt: str | None = None
    requires: RawCondition = None

    @model_validator(mode="after")
    def alt(self):
        _alt_required(self.image, self.image_alt, "image")
        return self


# --- interviews.yaml ----------------------------------------------------------------------


class Claim(Model):
    from_: str = Field(alias="from")
    to: str | None = None
    location: Key | None = None


class Statement(Model):
    key: Key
    text: Text
    claim: Claim | None = None


class Topic(Model):
    key: Key
    prompt: Text
    requires: RawCondition = None
    statements: list[Statement] = Field(min_length=1)


class Reaction(Model):
    evidence: Key
    statements: list[Statement] = Field(min_length=1)


class PersonInterview(Model):
    topics: list[Topic] = []
    reactions: list[Reaction] = []


# --- timeline.yaml ------------------------------------------------------------------------


class OneRef(Model):
    """Exactly one of evidence / statement (timeline sources, contradiction sides)."""

    evidence: Key | None = None
    statement: Ref | None = None

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.evidence is None) == (self.statement is None):
            raise ValueError("set exactly one of 'evidence' or 'statement'")
        return self

    @property
    def item(self) -> tuple[str, str]:
        return ("evidence", self.evidence) if self.evidence else ("statement", self.statement)


class TimelineEvent(Model):
    key: Key
    title: Text
    description: str | None = None
    from_: str = Field(alias="from")
    to: str | None = None
    location: Key | None = None
    people: list[Key] = []
    certainty: Literal["claimed", "verified"]
    source: OneRef
    requires: RawCondition  # required: no default for timeline events

    @model_validator(mode="after")
    def requires_present(self):
        if self.requires is None:
            raise ValueError("requires is required for timeline events")
        return self


# --- accusation.yaml ----------------------------------------------------------------------


class Option(Model):
    key: Key
    label: Text


class Cite(Model):
    min: int = Field(default=0, ge=0, le=5)
    max: int = Field(default=0, ge=0, le=5)
    prompt: str | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.min > self.max:
            raise ValueError("cite.min can't exceed cite.max")
        return self


class AccusationQuestion(Model):
    key: Key
    prompt: Text
    kind: Literal["person", "choice", "evidence"]
    required_for_solve: bool = False
    options: list[Option] | None = None
    cite: Cite = Cite()

    @model_validator(mode="after")
    def options_match_kind(self):
        if self.kind == "choice" and (not self.options or len(self.options) < 2):
            raise ValueError("choice questions need at least 2 options")
        if self.kind != "choice" and self.options:
            raise ValueError(f"{self.kind} questions don't take options")
        if self.kind == "evidence" and self.cite.min < 1:
            raise ValueError("evidence questions need cite.min ≥ 1")
        return self


class AccusationFile(Model):
    intro: str | None = None
    questions: list[AccusationQuestion] = Field(min_length=1)


# --- spoilers/contradictions.yaml ---------------------------------------------------------


class ContradictionEntry(Model):
    key: Key
    statement: Ref
    conflicts_with: OneRef
    explanation: Text
    accept_also: list[OneRef] = []


# --- spoilers/solution.yaml ---------------------------------------------------------------


class ProofSpec(Model):
    points: int = Field(ge=0)
    full: list[list[Ref]] = Field(min_length=1)
    partial: list[list[Ref]] = []


class AnswerSpec(Model):
    correct: Key | None = None
    points: int = Field(default=0, ge=0)
    proof: ProofSpec | None = None
    explanation: Text


class RedHerring(Model):
    person: Key
    suspicion: Text
    cleared_by: list[Ref] = Field(min_length=1)
    explanation: Text


class SolutionFile(Model):
    answers: dict[Key, AnswerSpec]
    summary: Text
    narrative: Text
    red_herrings: list[RedHerring] = []
    key_evidence: list[Key] = Field(min_length=1)
    answer_terms: list[Text] = []
    walkthrough: list[dict[str, Any]] = Field(min_length=1)  # parsed by the validator


# --- spoilers/hints.yaml ------------------------------------------------------------------

TIER_LEVELS = ("nudge", "pointer", "direction")


class HintTier(Model):
    level: Literal["nudge", "pointer", "direction"]
    text: Text


class HintTrack(Model):
    key: Key
    goal: Text
    priority: int = 100
    requires: RawCondition
    resolved_when: RawCondition
    mentions: list[Ref]
    tiers: list[HintTier]

    @model_validator(mode="after")
    def three_ordered_tiers(self):
        if tuple(t.level for t in self.tiers) != TIER_LEVELS:
            raise ValueError("tiers must be exactly: nudge, pointer, direction (in that order)")
        if self.requires is None or self.resolved_when is None:
            raise ValueError("requires and resolved_when are both required")
        return self


# --- the whole case -----------------------------------------------------------------------


class CaseBundle(BaseModel):
    """All files of one case, parsed. Built by loader.load_case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    case: CaseFile
    people: list[Person]
    locations: list[Location]
    evidence: list[Evidence]
    interviews: dict[Key, PersonInterview]
    timeline: list[TimelineEvent]
    accusation: AccusationFile
    contradictions: list[ContradictionEntry]
    solution: SolutionFile
    hints: list[HintTrack]


# File name → (bundle field, root model or list item model, is_list)
FILES: dict[str, tuple[str, type[BaseModel], str]] = {
    "case.yaml": ("case", CaseFile, "object"),
    "people.yaml": ("people", Person, "list"),
    "locations.yaml": ("locations", Location, "list"),
    "evidence.yaml": ("evidence", Evidence, "list"),
    "interviews.yaml": ("interviews", PersonInterview, "mapping"),
    "timeline.yaml": ("timeline", TimelineEvent, "list"),
    "accusation.yaml": ("accusation", AccusationFile, "object"),
    "spoilers/contradictions.yaml": ("contradictions", ContradictionEntry, "list"),
    "spoilers/solution.yaml": ("solution", SolutionFile, "object"),
    "spoilers/hints.yaml": ("hints", HintTrack, "list"),
}
