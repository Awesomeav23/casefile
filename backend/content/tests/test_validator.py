"""Validator: the fixture passes, and each rule catches its own broken fixture
(TESTING_PLAN §2.5). Broken fixtures are made by copying mini-case and changing one thing."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from content.validator import validate_case

CASES = Path(__file__).resolve().parents[3] / "content" / "cases"
MINI = CASES / "_fixtures" / "mini-case"


def mutate(tmp_path: Path, file: str, change: Callable[[object], object]) -> Path:
    """Copy mini-case (once per test) and edit one file in place; return values are ignored."""
    folder = tmp_path / "mini-case"
    if not folder.exists():
        shutil.copytree(MINI, folder)
    path = folder / file
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return folder


def by_key(items, key):
    return next(i for i in items if i["key"] == key)


def issues(folder: Path, rule: str, level: str = "error"):
    report = validate_case(folder)
    found = [i for i in report.issues if i.rule == rule and i.level == level]
    assert found, f"expected a {level} for {rule}; got:\n" + "\n".join(map(str, report.issues))
    return found


def test_mini_case_is_clean():
    report = validate_case(MINI)
    assert report.issues == [], "\n".join(map(str, report.issues))


def test_masterpiece_skeleton_validates():
    report = validate_case(CASES / "the-missing-masterpiece")
    assert report.errors == [], "\n".join(map(str, report.errors))


def test_mermaid_output():
    mermaid = validate_case(MINI, mermaid=True).mermaid
    assert mermaid.startswith("graph LR")
    assert "location__kitchen --> evidence__bus_ticket" in mermaid
    assert "evidence__bus_ticket --> contradiction__market_ticket" in mermaid


# --- stage 1: structure ---------------------------------------------------------------


def test_schema_error_names_file_key_and_field(tmp_path):
    folder = mutate(
        tmp_path, "evidence.yaml", lambda d: by_key(d, "empty-rack").update(kind="smell")
    )
    (issue,) = issues(folder, "schema")
    assert (issue.file, issue.key) == ("evidence.yaml", "empty-rack")
    assert issue.message.startswith("kind:")


def test_schema_nested_path_uses_keys(tmp_path):
    def change(d):
        d["ada"]["topics"][0]["statements"][0]["text"] = ""

    (issue,) = issues(mutate(tmp_path, "interviews.yaml", change), "schema")
    assert issue.key == "ada"
    assert issue.message.startswith("topics[the-morning].statements[at-market].text")


def test_missing_file(tmp_path):
    folder = mutate(tmp_path, "timeline.yaml", lambda d: None)
    (folder / "timeline.yaml").unlink()
    assert issues(folder, "missing-file")[0].file == "timeline.yaml"


def test_invalid_yaml_reports_line(tmp_path):
    folder = mutate(tmp_path, "people.yaml", lambda d: None)
    (folder / "people.yaml").write_text("- key: ada\n  name: [unclosed\n")
    assert "line" in issues(folder, "yaml")[0].message


def test_duplicate_yaml_mapping_key(tmp_path):
    folder = mutate(tmp_path, "people.yaml", lambda d: None)
    text = (
        (folder / "people.yaml")
        .read_text()
        .replace("role: Neighbour", "role: Neighbour\n  role: Again", 1)
    )
    (folder / "people.yaml").write_text(text)
    assert "duplicate key" in issues(folder, "yaml")[0].message


def test_duplicate_item_key(tmp_path):
    folder = mutate(tmp_path, "locations.yaml", lambda d: d.append(dict(d[0])))
    assert issues(folder, "duplicate-key")[0].key == "shed"


def test_duplicate_statement_key_per_person(tmp_path):
    def change(d):
        d["ben"]["topics"][1]["statements"][0]["key"] = "at-gym"

    assert (
        issues(mutate(tmp_path, "interviews.yaml", change), "duplicate-key")[0].key == "ben/at-gym"
    )


def test_slug_must_match_folder(tmp_path):
    folder = mutate(tmp_path, "case.yaml", lambda d: d.update(slug="other-case"))
    assert issues(folder, "reference")[0].key == "slug"


def test_invalid_condition(tmp_path):
    folder = mutate(
        tmp_path, "evidence.yaml", lambda d: by_key(d, "gym-pass").update(requires={"all": []})
    )
    (issue,) = issues(folder, "condition")
    assert issue.key == "gym-pass" and "at least one" in issue.message


def test_condition_reference_must_exist(tmp_path):
    folder = mutate(
        tmp_path,
        "evidence.yaml",
        lambda d: by_key(d, "gym-pass").update(requires={"asked": "ben/nothing"}),
    )
    assert "unknown topic 'ben/nothing'" in issues(folder, "reference")[0].message


@pytest.mark.parametrize(
    "file, change, fragment",
    [
        (
            "evidence.yaml",
            lambda d: by_key(d, "empty-rack").update(location="attic"),
            "unknown location 'attic'",
        ),
        (
            "evidence.yaml",
            lambda d: by_key(d, "bus-ticket").update(people=["zed"]),
            "unknown person 'zed'",
        ),
        (
            "timeline.yaml",
            lambda d: by_key(d, "theft").update(source={"evidence": "nothing"}),
            "unknown evidence",
        ),
        (
            "spoilers/contradictions.yaml",
            lambda d: d[0].update(statement="ada/never-said"),
            "unknown statement",
        ),
        (
            "spoilers/hints.yaml",
            lambda d: d[0].update(mentions=["evidence:ghost"]),
            "unknown evidence 'ghost'",
        ),
        (
            "spoilers/solution.yaml",
            lambda d: d["answers"]["culprit"].update(correct="nobody"),
            "isn't a suspect",
        ),
        (
            "spoilers/solution.yaml",
            lambda d: d["answers"]["motive"].update(correct="boredom"),
            "isn't one of the options",
        ),
        (
            "spoilers/solution.yaml",
            lambda d: d["answers"].pop("motive"),
            "no answer for this accusation question",
        ),
        (
            "spoilers/solution.yaml",
            lambda d: d["answers"]["motive"]["proof"].update(full=[["location:shed"]]),
            "isn't citable",
        ),
        (
            "spoilers/solution.yaml",
            lambda d: d.update(key_evidence=["ghost"]),
            "unknown evidence 'ghost'",
        ),
        (
            "spoilers/solution.yaml",
            lambda d: d["red_herrings"][0].update(person="ada"),
            "the culprit can't be a red herring",
        ),
    ],
)
def test_reference_rules(tmp_path, file, change, fragment):
    found = issues(mutate(tmp_path, file, change), "reference")
    assert any(fragment in i.message for i in found), [str(i) for i in found]


def test_interview_for_unknown_person(tmp_path):
    folder = mutate(tmp_path, "interviews.yaml", lambda d: d.update(zed={"topics": []}))
    assert issues(folder, "reference")[0].key == "zed"


def test_missing_asset(tmp_path):
    folder = mutate(tmp_path, "case.yaml", lambda d: d.update(cover_image="assets/missing.webp"))
    assert "doesn't exist" in issues(folder, "asset")[0].message


def test_asset_must_be_webp(tmp_path):
    folder = mutate(tmp_path, "case.yaml", lambda d: d.update(cover_image="assets/cover.png"))
    assert ".webp" in issues(folder, "asset")[0].message


def test_asset_must_be_real_webp(tmp_path):
    folder = mutate(tmp_path, "case.yaml", lambda d: None)
    (folder / "assets" / "cover.webp").write_bytes(b"not an image at all")
    assert "valid WebP" in issues(folder, "asset")[0].message


def test_raw_html_rejected(tmp_path):
    folder = mutate(
        tmp_path, "evidence.yaml", lambda d: by_key(d, "bus-ticket").update(body="<b>09:40</b>")
    )
    assert issues(folder, "html")[0].key == "bus-ticket"


@pytest.mark.parametrize(
    "change, fragment",
    [
        (lambda d: by_key(d, "theft").update({"from": "ten"}), "isn't HH:MM"),
        (lambda d: by_key(d, "ada-claim").update({"to": "08:00"}), "'to' is before 'from'"),
        (lambda d: by_key(d, "ada-claim").update({"from": "09:30"}), "doesn't match the claim"),
        (lambda d: by_key(d, "ada-claim").update(certainty="verified"), "must be 'claimed'"),
    ],
)
def test_timeline_rules(tmp_path, change, fragment):
    found = issues(mutate(tmp_path, "timeline.yaml", change), "timeline")
    assert any(fragment in i.message for i in found), [str(i) for i in found]


# --- stage 2: logic --------------------------------------------------------------------


def unreachable(key):
    """A condition that can never hold: the item depends on itself."""
    return {"discovered": f"evidence:{key}"}


def test_f1_and_f2_unreachable_proof_and_key_evidence(tmp_path):
    folder = mutate(
        tmp_path,
        "evidence.yaml",
        lambda d: by_key(d, "repair-quote").update(requires=unreachable("repair-quote")),
    )
    assert any("no full proof set" in i.message for i in issues(folder, "F1"))
    assert any("repair-quote" in i.message for i in issues(folder, "F2"))


def test_f3_orphan_is_a_warning(tmp_path):
    def change(d):
        d.append(
            {
                "key": "lost-glove",
                "title": "Glove",
                "kind": "object",
                "summary": "A glove.",
                "body": "A glove.",
                "requires": unreachable("lost-glove"),
            }
        )

    folder = mutate(tmp_path, "evidence.yaml", change)
    assert issues(folder, "F3", level="warning")[0].key == "lost-glove"
    assert validate_case(folder).ok


def test_f4_culprit_must_appear_early(tmp_path):
    folder = mutate(
        tmp_path,
        "people.yaml",
        lambda d: by_key(d, "ada").update(requires={"examined": "gym-pass"}),
    )
    assert issues(folder, "F4")[0].key == "ada"


def test_f5_every_other_suspect_needs_a_red_herring(tmp_path):
    folder = mutate(tmp_path, "spoilers/solution.yaml", lambda d: d.update(red_herrings=[]))
    assert "ben" in issues(folder, "F5")[0].message


def test_unreachable_contradiction(tmp_path):
    folder = mutate(
        tmp_path,
        "evidence.yaml",
        lambda d: by_key(d, "bus-ticket").update(requires=unreachable("bus-ticket")),
    )
    assert issues(folder, "unreachable-contradiction")[0].key == "market-ticket"


@pytest.mark.parametrize(
    "change, fragment",
    [
        (lambda d: d["walkthrough"].insert(0, {"ask": "ben/the-secret"}), "isn't available yet"),
        (
            lambda d: d["walkthrough"].__setitem__(
                2, {"flag": {"statement": "ada/at-market", "evidence": "empty-rack"}}
            ),
            "both sides must be discovered",
        ),
        (
            lambda d: d["walkthrough"].insert(2, {"visit": "shed"})
            or d["walkthrough"].__setitem__(
                3, {"flag": {"statement": "ada/at-market", "evidence": "empty-rack"}}
            ),
            "isn't an authored contradiction",
        ),
        (
            lambda d: d["walkthrough"][-1]["accuse"]["motive"].update(cite=["bus-ticket"]),
            "it must be solved and airtight",
        ),
        (
            lambda d: d["walkthrough"][-1]["accuse"]["motive"].update(cite=["gym-pass"]),
            "not discovered yet",
        ),
        (lambda d: d["walkthrough"].pop(), "must end with an accuse step"),
        (lambda d: d["walkthrough"].insert(0, {"teleport": "shed"}), "unknown action"),
    ],
)
def test_f6_walkthrough(tmp_path, change, fragment):
    found = issues(mutate(tmp_path, "spoilers/solution.yaml", change), "F6")
    assert any(fragment in i.message for i in found), [str(i) for i in found]


def test_f12_mention_must_be_guaranteed(tmp_path):
    folder = mutate(
        tmp_path,
        "spoilers/hints.yaml",
        lambda d: d[0].update(requires={"asked": "ada/the-morning"}),
    )
    assert any("bus-ticket" in i.message for i in issues(folder, "F12"))


def test_f12_track_never_offered(tmp_path):
    folder = mutate(
        tmp_path,
        "spoilers/hints.yaml",
        lambda d: d[1].update(
            requires={"examined": "repair-quote"}, resolved_when={"examined": "gym-pass"}
        ),
    )
    mutate(
        tmp_path,
        "evidence.yaml",
        lambda d: by_key(d, "repair-quote").update(requires=unreachable("repair-quote")),
    )
    assert any("never offered" in i.message for i in issues(folder, "F12"))


def test_f12_track_only_relevant_after_resolved(tmp_path):
    folder = mutate(
        tmp_path,
        "spoilers/hints.yaml",
        lambda d: d[1].update(requires={"examined": "repair-quote"}),
    )
    assert any("already resolved" in i.message for i in issues(folder, "F12"))


def test_f12_tiers_must_be_exactly_three_in_order(tmp_path):
    folder = mutate(tmp_path, "spoilers/hints.yaml", lambda d: d[0]["tiers"].pop())
    assert "nudge, pointer, direction" in issues(folder, "schema")[0].message


def test_f13_uncovered_proof_item_is_a_warning(tmp_path):
    folder = mutate(tmp_path, "spoilers/hints.yaml", lambda d: d.pop(1))
    assert "repair-quote" in issues(folder, "F13", level="warning")[0].message


def test_f14_giveaway_terms_are_a_warning(tmp_path):
    def change(d):
        d[1]["tiers"][2]["text"] = (
            "Ada took the bicycle because she needed a bicycle while hers was being repaired."
        )

    found = issues(mutate(tmp_path, "spoilers/hints.yaml", change), "F14", level="warning")
    assert found[0].key == "why-would-she.direction"


def test_template_has_every_file_and_parses():
    from content.schema import FILES

    template = CASES / "_template"
    for file in FILES:
        assert (template / file).is_file(), file
        yaml.safe_load((template / file).read_text())
