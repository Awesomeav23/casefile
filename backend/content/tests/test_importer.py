"""import_case (TESTING_PLAN §2.6)."""

import shutil
from io import StringIO
from pathlib import Path

import pytest
import yaml
from django.core.management import CommandError, call_command

from content import importer
from content.assets import collect_case_assets
from content.importer import ImportRefused, import_case
from content.models import (
    AccusationOption,
    AnswerKey,
    Case,
    CaseImport,
    CaseSolution,
    Contradiction,
    Evidence,
    Hint,
    HintTrack,
    Location,
    Person,
    RedHerring,
    Statement,
    TimelineEvent,
    Topic,
)
from content.tests.test_validator import CASES, MINI

pytestmark = pytest.mark.django_db
MASTERPIECE = CASES / "the-missing-masterpiece"


@pytest.fixture
def mini(tmp_path) -> Path:
    folder = tmp_path / "mini-case"
    shutil.copytree(MINI, folder)
    return folder


def edit(folder: Path, file: str, change) -> None:
    path = folder / file
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def by_key(items, key):
    return next(i for i in items if i["key"] == key)


# --- first import ------------------------------------------------------------------------


def test_first_import_creates_everything(mini):
    result = import_case(mini)
    case = Case.objects.get(slug="mini-case")
    assert (result.action, case.status, case.content_version) == ("created", "draft", 1)
    assert Person.objects.filter(case=case).count() == 2
    assert Location.objects.filter(case=case).count() == 2
    assert Evidence.objects.filter(case=case).count() == 4
    assert Topic.objects.filter(case=case).count() == 3
    assert Statement.objects.filter(case=case).count() == 4  # 3 topic statements + 1 reaction
    assert TimelineEvent.objects.filter(case=case).count() == 3
    assert AccusationOption.objects.filter(question__case=case).count() == 4
    assert Contradiction.objects.filter(case=case).count() == 1
    assert AnswerKey.objects.filter(question__case=case).count() == 2
    assert RedHerring.objects.filter(case=case).count() == 1
    assert HintTrack.objects.filter(case=case).count() == 2
    assert Hint.objects.filter(track__case=case).count() == 6
    assert CaseSolution.objects.get(case=case).key_evidence == ["bus-ticket", "repair-quote"]
    assert CaseImport.objects.filter(case=case).count() == 1


def test_masterpiece_imports():
    import_case(MASTERPIECE)
    case = Case.objects.get(slug="the-missing-masterpiece")
    assert Evidence.objects.filter(case=case).count() == 13
    assert HintTrack.objects.filter(case=case).count() == 6
    assert Hint.objects.filter(track__case=case).count() == 18


def test_requires_is_stored_as_the_effective_condition(mini):
    import_case(mini)
    quote = Evidence.objects.get(key="repair-quote")
    assert quote.requires == {"all": [{"visited": "kitchen"}, {"asked": "ben/the-bike"}]}
    topic = Topic.objects.get(key="the-bike")
    assert topic.requires == {"discovered": "person:ben"}
    assert Person.objects.get(key="ada").requires == "start"


def test_relationships_and_typed_refs(mini):
    import_case(mini)
    reaction = Statement.objects.get(key="ticket-reaction")
    assert (reaction.topic, reaction.reaction_evidence.key) == (None, "bus-ticket")
    claim = Statement.objects.get(key="at-market")
    assert (claim.claim_from.hour, claim.claim_to.hour) == (9, 12)
    event = TimelineEvent.objects.get(key="ada-claim")
    assert event.source_statement == claim and [p.key for p in event.people.all()] == ["ada"]
    assert set(Evidence.objects.get(key="bus-ticket").people.values_list("key", flat=True)) == {
        "ada"
    }
    motive = AnswerKey.objects.get(question__key="motive")
    assert motive.proof_full == [[{"type": "evidence", "key": "repair-quote"}]]
    assert motive.proof_partial == [[{"type": "statement", "key": "ben/bike-broke"}]]
    track = HintTrack.objects.get(key="check-adas-morning")
    assert {"type": "statement", "key": "ada/at-market"} in track.mentions
    assert [h.level for h in track.tiers.all()] == ["nudge", "pointer", "direction"]


def test_cover_image_path_matches_collected_assets(mini, tmp_path):
    import_case(mini)
    out = tmp_path / "static_src"
    collect_case_assets([mini], out)
    stored = Case.objects.get(slug="mini-case").cover_image
    assert stored.startswith("cases/mini-case/") and stored.endswith(".webp")
    assert (out / stored).is_file()


# --- re-imports --------------------------------------------------------------------------


def test_unchanged_reimport_is_a_no_op(mini):
    import_case(mini)
    assert import_case(mini).action == "unchanged"
    assert CaseImport.objects.count() == 1


def test_text_edit_updates_in_place(mini):
    import_case(mini)
    before = Evidence.objects.get(key="bus-ticket").pk
    edit(
        mini,
        "evidence.yaml",
        lambda d: by_key(d, "bus-ticket").update(summary="A crumpled bus ticket."),
    )
    result = import_case(mini)
    ticket = Evidence.objects.get(key="bus-ticket")
    assert (result.action, result.breaking, ticket.pk) == ("updated", False, before)
    assert ticket.summary == "A crumpled bus ticket."
    assert Case.objects.get().content_version == 1


def test_added_item_is_inserted(mini):
    import_case(mini)
    edit(
        mini,
        "evidence.yaml",
        lambda d: d.append(
            {
                "key": "receipt",
                "title": "Receipt",
                "kind": "record",
                "location": "kitchen",
                "summary": "s",
                "body": "b",
            }
        ),
    )
    assert not import_case(mini).breaking
    assert Evidence.objects.filter(key="receipt").exists()


def test_removed_key_on_a_draft_is_applied(mini):
    import_case(mini)
    edit(mini, "timeline.yaml", lambda d: d.remove(by_key(d, "theft")))
    result = import_case(mini)
    assert result.breaking and not TimelineEvent.objects.filter(key="theft").exists()
    assert Case.objects.get().content_version == 2


def test_breaking_change_to_a_published_case_needs_force(mini):
    import_case(mini, publish=True)
    edit(mini, "timeline.yaml", lambda d: d.remove(by_key(d, "theft")))
    with pytest.raises(ImportRefused, match="timeline_event 'theft' removed"):
        import_case(mini)
    assert TimelineEvent.objects.filter(key="theft").exists()  # nothing changed
    result = import_case(mini, force=True)
    assert result.breaking and Case.objects.get().content_version == 2
    assert CaseImport.objects.filter(breaking=True).count() == 1


def test_changed_answer_on_a_published_case_is_breaking(mini):
    import_case(mini, publish=True)
    edit(mini, "spoilers/solution.yaml", lambda d: d["answers"]["motive"].update(points=25))
    with pytest.raises(ImportRefused, match="answer for 'motive' changed"):
        import_case(mini)


def test_invalid_case_is_refused_and_writes_nothing(mini):
    edit(mini, "evidence.yaml", lambda d: by_key(d, "bus-ticket").update(location="attic"))
    with pytest.raises(ImportRefused, match="unknown location 'attic'"):
        import_case(mini)
    assert not Case.objects.exists()


def test_import_is_transactional(mini, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(importer, "_import_hints", explode)
    with pytest.raises(RuntimeError):
        import_case(mini)
    assert not Case.objects.exists() and not Person.objects.exists()


def test_publish_sets_status_and_timestamp(mini):
    import_case(mini)
    result = import_case(mini, publish=True)
    case = Case.objects.get()
    assert (result.action, case.status) == ("published", "published")
    assert case.published_at is not None
    assert CaseImport.objects.filter(case=case, report__published=True).count() == 1


# --- management commands ------------------------------------------------------------------


def run(*args):
    out = StringIO()
    call_command("import_case", *args, stdout=out)
    return out.getvalue()


def test_import_command(mini):
    assert "✓ mini-case: created (draft, version 1)" in run(str(mini))
    assert "= mini-case: unchanged" in run(str(mini))


def test_import_command_refuses_invalid(mini):
    edit(mini, "evidence.yaml", lambda d: by_key(d, "bus-ticket").update(location="attic"))
    with pytest.raises(CommandError, match="refused"):
        run(str(mini))


def test_import_all_imports_real_cases():
    assert "the-missing-masterpiece: created" in run("--all")
    assert not Case.objects.filter(slug="mini-case").exists()


def test_collect_case_assets_command(tmp_path, settings):
    settings.CASE_ASSETS_DIR = tmp_path / "static_src"
    out = StringIO()
    call_command("collect_case_assets", "--include-fixtures", stdout=out)
    copied = sorted(
        p.relative_to(tmp_path / "static_src").as_posix()
        for p in (tmp_path / "static_src").rglob("*.webp")
    )
    assert any(p.startswith("cases/the-missing-masterpiece/") for p in copied)
    assert any(p.startswith("cases/mini-case/") for p in copied)
