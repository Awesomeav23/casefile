"""Database constraints on content tables (TESTING_PLAN §3)."""

import datetime as dt

import pytest
from django.db import IntegrityError, transaction
from django.db.models import RestrictedError

from content.models import (
    AccusationQuestion,
    Case,
    Evidence,
    Hint,
    HintTrack,
    Location,
    Person,
    Statement,
    TimelineEvent,
    Topic,
)

pytestmark = pytest.mark.django_db

T0 = dt.datetime(2026, 3, 13, 21, 0, tzinfo=dt.UTC)


@pytest.fixture
def case():
    return Case.objects.create(
        slug="c",
        title="C",
        tagline="t",
        difficulty="standard",
        estimated_minutes=10,
        world_date=dt.date(2026, 3, 13),
        cover_image="x",
        cover_alt="x",
        briefing="b",
        objective="o",
        copyright="©",
        format_version=1,
        content_hash="0" * 64,
    )


@pytest.fixture
def world(case):
    person = Person.objects.create(
        case=case,
        key="ada",
        name="Ada",
        role="r",
        summary="s",
        default_reaction="d",
        is_suspect=True,
        requires="start",
    )
    location = Location.objects.create(
        case=case, key="shed", name="Shed", description="d", requires="start"
    )
    evidence = Evidence.objects.create(
        case=case,
        key="ticket",
        title="T",
        kind="record",
        summary="s",
        body="b",
        location=location,
        requires={"visited": "shed"},
    )
    topic = Topic.objects.create(
        case=case, person=person, key="morning", prompt="p", requires="start"
    )
    return {
        "case": case,
        "person": person,
        "location": location,
        "evidence": evidence,
        "topic": topic,
    }


def fails(make):
    with pytest.raises(IntegrityError), transaction.atomic():
        make()


def test_keys_are_unique_within_a_case(world):
    c = world["case"]
    fails(
        lambda: Location.objects.create(
            case=c, key="shed", name="x", description="d", requires="start"
        )
    )


def test_statement_needs_exactly_one_trigger(world):
    base = {"case": world["case"], "person": world["person"], "text": "t"}
    fails(lambda: Statement.objects.create(key="none", **base))
    fails(
        lambda: Statement.objects.create(
            key="both", topic=world["topic"], reaction_evidence=world["evidence"], **base
        )
    )
    Statement.objects.create(key="ok", topic=world["topic"], **base)


def test_statement_keys_unique_per_person(world):
    base = {"case": world["case"], "person": world["person"], "text": "t", "topic": world["topic"]}
    Statement.objects.create(key="s", **base)
    fails(lambda: Statement.objects.create(key="s", **base))


def test_statement_claim_order(world):
    fails(
        lambda: Statement.objects.create(
            case=world["case"],
            person=world["person"],
            key="s",
            text="t",
            topic=world["topic"],
            claim_from=T0,
            claim_to=T0 - dt.timedelta(hours=1),
        )
    )


def test_timeline_needs_exactly_one_source_and_ordered_times(world):
    base = {
        "case": world["case"],
        "title": "t",
        "certainty": "verified",
        "requires": "start",
        "starts_at": T0,
    }
    fails(lambda: TimelineEvent.objects.create(key="none", **base))
    fails(
        lambda: TimelineEvent.objects.create(
            key="backwards",
            source_evidence=world["evidence"],
            ends_at=T0 - dt.timedelta(minutes=1),
            **base,
        )
    )
    TimelineEvent.objects.create(key="ok", source_evidence=world["evidence"], **base)


def test_question_cite_range(world):
    base = {"case": world["case"], "prompt": "p", "kind": "choice"}
    fails(lambda: AccusationQuestion.objects.create(key="a", cite_min=2, cite_max=1, **base))
    fails(lambda: AccusationQuestion.objects.create(key="b", cite_min=0, cite_max=6, **base))


def test_hint_tier_must_match_level(world):
    track = HintTrack.objects.create(
        case=world["case"], key="t", goal="g", requires="start", resolved_when="start"
    )
    fails(lambda: Hint.objects.create(track=track, tier=1, level="direction", text="x"))
    Hint.objects.create(track=track, tier=1, level="nudge", text="x")
    fails(lambda: Hint.objects.create(track=track, tier=1, level="nudge", text="again"))


def test_image_needs_alt_text(world):
    fails(
        lambda: Location.objects.create(
            case=world["case"],
            key="yard",
            name="Y",
            description="d",
            image="a.webp",
            requires="start",
        )
    )


def test_evidence_kind_is_checked(world):
    fails(
        lambda: Evidence.objects.create(
            case=world["case"],
            key="x",
            title="x",
            kind="smell",
            summary="s",
            body="b",
            requires="start",
        )
    )


def test_location_with_evidence_is_protected(world):
    with pytest.raises(RestrictedError):
        world["location"].delete()


def test_deleting_a_case_removes_its_content(world):
    world["case"].delete()
    assert (
        not Person.objects.exists() and not Evidence.objects.exists() and not Topic.objects.exists()
    )
