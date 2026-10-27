"""Case content tables (docs/DATA_MODEL.md §3–4). Rows are written only by `import_case`.

🔒 Spoiler models (Contradiction, AnswerKey, CaseSolution, RedHerring, HintTrack, Hint) must
never be imported by player-facing serializers (ARCHITECTURE §3.4).

Conventions: keys are the author's stable slugs; `requires` holds the *effective* condition
(authored + implicit rules, see content/compile.py) as JSON; in-world times are stored as UTC
wall-clock timestamps (the "UTC" has no real-world meaning).
"""

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

EVIDENCE_KINDS = ("document", "photo", "object", "record", "correspondence", "transcript")


def _choices(*values: str) -> list[tuple[str, str]]:
    return [(v, v) for v in values]


def _one_of(*fields: str) -> Q:
    """Exactly one of the nullable FK fields is set."""
    terms = []
    for chosen in fields:
        term = Q(**{f"{chosen}__isnull": False})
        for other in fields:
            if other != chosen:
                term &= Q(**{f"{other}__isnull": True})
        terms.append(term)
    result = terms[0]
    for term in terms[1:]:
        result |= term
    return result


def _alt_when_image(image: str, alt: str) -> Q:
    return Q(**{image: ""}) | ~Q(**{alt: ""})


class Case(models.Model):
    DIFFICULTIES = ("introductory", "standard", "hard")
    STATUSES = ("draft", "published", "retired")

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300)
    difficulty = models.CharField(max_length=20, choices=_choices(*DIFFICULTIES))
    estimated_minutes = models.PositiveSmallIntegerField()
    tags = ArrayField(models.CharField(max_length=80), default=list, blank=True)
    content_notes = ArrayField(models.CharField(max_length=200), default=list, blank=True)
    world_date = models.DateField()
    era_note = models.TextField(blank=True)
    cover_image = models.CharField(max_length=300)
    cover_alt = models.CharField(max_length=500)
    briefing = models.TextField()
    objective = models.TextField()
    accusation_intro = models.TextField(blank=True)
    copyright = models.CharField(max_length=200)
    rating_thresholds = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=_choices(*STATUSES), default="draft", db_index=True
    )
    format_version = models.PositiveSmallIntegerField()
    content_version = models.PositiveIntegerField(default=1)
    content_hash = models.CharField(max_length=64)
    sort_order = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "slug"]
        indexes = [GinIndex(fields=["tags"], name="content_case_tags_gin")]
        constraints = [
            CheckConstraint(
                condition=Q(difficulty__in=("introductory", "standard", "hard")),
                name="case_difficulty_valid",
            ),
            CheckConstraint(
                condition=Q(status__in=("draft", "published", "retired")), name="case_status_valid"
            ),
            CheckConstraint(condition=Q(estimated_minutes__gt=0), name="case_minutes_positive"),
        ]

    def __str__(self):
        return self.title


class CaseContent(models.Model):
    """Shared shape: belongs to a case, has a key unique within it, keeps YAML order."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="+")
    key = models.CharField(max_length=80)
    sort_order = models.IntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["sort_order"]

    def __str__(self):
        return self.key


class Person(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="people")
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    summary = models.CharField(max_length=500)
    bio = models.TextField(blank=True)
    default_reaction = models.TextField()
    is_suspect = models.BooleanField()
    portrait = models.CharField(max_length=300, blank=True)
    portrait_alt = models.CharField(max_length=500, blank=True)
    requires = models.JSONField()

    class Meta(CaseContent.Meta):
        constraints = [
            UniqueConstraint(fields=["case", "key"], name="person_unique_key"),
            CheckConstraint(
                condition=_alt_when_image("portrait", "portrait_alt"), name="person_portrait_alt"
            ),
        ]
        indexes = [models.Index(fields=["case", "is_suspect"], name="person_case_suspect")]


class Location(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.CharField(max_length=300, blank=True)
    image_alt = models.CharField(max_length=500, blank=True)
    requires = models.JSONField()

    class Meta(CaseContent.Meta):
        constraints = [
            UniqueConstraint(fields=["case", "key"], name="location_unique_key"),
            CheckConstraint(condition=_alt_when_image("image", "image_alt"), name="location_alt"),
        ]


class Evidence(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="evidence")
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=_choices(*EVIDENCE_KINDS))
    summary = models.CharField(max_length=500)
    body = models.TextField()
    location = models.ForeignKey(
        Location, on_delete=models.RESTRICT, null=True, blank=True, related_name="evidence"
    )
    people = models.ManyToManyField(Person, blank=True, related_name="evidence")
    image = models.CharField(max_length=300, blank=True)
    image_alt = models.CharField(max_length=500, blank=True)
    requires = models.JSONField()

    class Meta(CaseContent.Meta):
        verbose_name_plural = "evidence"
        constraints = [
            UniqueConstraint(fields=["case", "key"], name="evidence_unique_key"),
            CheckConstraint(condition=Q(kind__in=EVIDENCE_KINDS), name="evidence_kind_valid"),
            CheckConstraint(condition=_alt_when_image("image", "image_alt"), name="evidence_alt"),
        ]


class Topic(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="topics")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="topics")
    prompt = models.CharField(max_length=500)
    requires = models.JSONField()

    class Meta(CaseContent.Meta):
        constraints = [UniqueConstraint(fields=["person", "key"], name="topic_unique_key")]

    @property
    def ref(self) -> str:
        return f"{self.person.key}/{self.key}"


class Statement(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="statements")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="statements")
    text = models.TextField()
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, null=True, blank=True, related_name="statements"
    )
    reaction_evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, null=True, blank=True, related_name="reactions"
    )
    claim_from = models.DateTimeField(null=True, blank=True)
    claim_to = models.DateTimeField(null=True, blank=True)
    claim_location = models.ForeignKey(
        Location, on_delete=models.RESTRICT, null=True, blank=True, related_name="+"
    )

    class Meta(CaseContent.Meta):
        constraints = [
            UniqueConstraint(fields=["person", "key"], name="statement_unique_key"),
            CheckConstraint(
                condition=_one_of("topic", "reaction_evidence"), name="statement_one_trigger"
            ),
            CheckConstraint(
                condition=Q(claim_to__isnull=True)
                | Q(claim_from__isnull=True)
                | Q(claim_to__gte=models.F("claim_from")),
                name="statement_claim_order",
            ),
        ]

    @property
    def ref(self) -> str:
        return f"{self.person.key}/{self.key}"


class TimelineEvent(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="timeline")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.RESTRICT, null=True, blank=True, related_name="+"
    )
    people = models.ManyToManyField(Person, blank=True, related_name="+")
    certainty = models.CharField(max_length=10, choices=_choices("claimed", "verified"))
    source_evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    source_statement = models.ForeignKey(
        Statement, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    requires = models.JSONField()

    class Meta(CaseContent.Meta):
        ordering = ["starts_at", "sort_order"]
        indexes = [models.Index(fields=["case", "starts_at"], name="timeline_case_start")]
        constraints = [
            UniqueConstraint(fields=["case", "key"], name="timeline_unique_key"),
            CheckConstraint(
                condition=_one_of("source_evidence", "source_statement"), name="timeline_one_source"
            ),
            CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gte=models.F("starts_at")),
                name="timeline_order",
            ),
            CheckConstraint(
                condition=Q(certainty__in=("claimed", "verified")), name="timeline_certainty"
            ),
        ]


class AccusationQuestion(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="questions")
    prompt = models.CharField(max_length=500)
    kind = models.CharField(max_length=10, choices=_choices("person", "choice", "evidence"))
    required_for_solve = models.BooleanField(default=False)
    cite_min = models.PositiveSmallIntegerField(default=0)
    cite_max = models.PositiveSmallIntegerField(default=0)
    cite_prompt = models.CharField(max_length=500, blank=True)

    class Meta(CaseContent.Meta):
        constraints = [
            UniqueConstraint(fields=["case", "key"], name="question_unique_key"),
            CheckConstraint(
                condition=Q(kind__in=("person", "choice", "evidence")), name="question_kind"
            ),
            CheckConstraint(
                condition=Q(cite_min__lte=models.F("cite_max")) & Q(cite_max__lte=5),
                name="question_cite_range",
            ),
        ]


class AccusationOption(models.Model):
    question = models.ForeignKey(
        AccusationQuestion, on_delete=models.CASCADE, related_name="options"
    )
    key = models.CharField(max_length=80)
    label = models.CharField(max_length=500)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        constraints = [UniqueConstraint(fields=["question", "key"], name="option_unique_key")]

    def __str__(self):
        return self.key


class CaseImport(models.Model):
    """Audit row for every import that changed something."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="imports")
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.CharField(max_length=150)
    content_hash = models.CharField(max_length=64)
    content_version = models.PositiveIntegerField()
    breaking = models.BooleanField(default=False)
    report = models.JSONField(default=dict)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self):
        return f"{self.case.slug} v{self.content_version} @ {self.imported_at:%Y-%m-%d %H:%M}"


# --- 🔒 Spoiler tables --------------------------------------------------------------------


class Contradiction(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="contradictions")
    statement = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name="+")
    conflicts_evidence = models.ForeignKey(
        Evidence, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    conflicts_statement = models.ForeignKey(
        Statement, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    accept_also = models.JSONField(default=list, blank=True)  # [{"type": ..., "key": ...}]
    explanation = models.TextField()

    class Meta(CaseContent.Meta):
        constraints = [
            UniqueConstraint(fields=["case", "key"], name="contradiction_unique_key"),
            CheckConstraint(
                condition=_one_of("conflicts_evidence", "conflicts_statement"),
                name="contradiction_one_conflict",
            ),
        ]


class AnswerKey(models.Model):
    question = models.OneToOneField(
        AccusationQuestion, on_delete=models.CASCADE, related_name="answer_key"
    )
    # NULL (not "") means "no answer": evidence-kind questions are scored on proof only.
    correct_value = models.CharField(max_length=80, null=True, blank=True)  # noqa: DJ001
    points = models.PositiveSmallIntegerField(default=0)
    proof_points = models.PositiveSmallIntegerField(default=0)
    proof_full = models.JSONField(default=list, blank=True)  # [[{"type","key"}, ...], ...]
    proof_partial = models.JSONField(default=list, blank=True)
    explanation = models.TextField()

    def __str__(self):
        return f"answer: {self.question.key}"


class CaseSolution(models.Model):
    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="solution")
    summary = models.TextField()
    narrative = models.TextField()
    key_evidence = ArrayField(models.CharField(max_length=80), default=list)
    answer_terms = ArrayField(models.CharField(max_length=200), default=list, blank=True)
    walkthrough = models.JSONField(default=list)

    def __str__(self):
        return f"solution: {self.case.slug}"


class RedHerring(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="red_herrings")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="+")
    suspicion = models.TextField()
    cleared_by = models.JSONField(default=list)  # [{"type","key"}, ...]
    explanation = models.TextField()

    class Meta:
        constraints = [UniqueConstraint(fields=["case", "person"], name="redherring_unique")]

    def __str__(self):
        return f"red herring: {self.person.key}"


class HintTrack(CaseContent):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="hint_tracks")
    goal = models.CharField(max_length=120)
    priority = models.SmallIntegerField(default=100)
    requires = models.JSONField()
    resolved_when = models.JSONField()
    mentions = models.JSONField(default=list, blank=True)  # [{"type","key"}, ...]

    class Meta(CaseContent.Meta):
        ordering = ["priority", "sort_order"]
        constraints = [UniqueConstraint(fields=["case", "key"], name="hinttrack_unique_key")]


class Hint(models.Model):
    LEVELS = ("nudge", "pointer", "direction")

    track = models.ForeignKey(HintTrack, on_delete=models.CASCADE, related_name="tiers")
    tier = models.PositiveSmallIntegerField()
    level = models.CharField(max_length=10, choices=_choices(*LEVELS))
    text = models.TextField()

    class Meta:
        ordering = ["tier"]
        constraints = [
            UniqueConstraint(fields=["track", "tier"], name="hint_unique_tier"),
            CheckConstraint(
                condition=Q(tier=1, level="nudge")
                | Q(tier=2, level="pointer")
                | Q(tier=3, level="direction"),
                name="hint_tier_level",
            ),
        ]

    def __str__(self):
        return f"{self.track.key} · {self.level}"
