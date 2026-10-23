import shutil
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from content.tests.test_validator import MINI


def run(*args):
    out = StringIO()
    call_command("validate_case", *args, stdout=out)
    return out.getvalue()


def test_valid_case_passes():
    assert "✓ mini-case: valid" in run(str(MINI))


def test_invalid_case_fails_with_readable_issues(tmp_path):
    broken = tmp_path / "mini-case"
    shutil.copytree(MINI, broken)
    (broken / "spoilers" / "hints.yaml").unlink()
    with pytest.raises(CommandError, match="1 case has errors"):
        run(str(broken))


def test_issue_lines_are_printed(tmp_path, capsys):
    broken = tmp_path / "mini-case"
    shutil.copytree(MINI, broken)
    (broken / "spoilers" / "hints.yaml").unlink()
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("validate_case", str(broken), stdout=out)
    assert "[error] missing-file: spoilers/hints.yaml" in out.getvalue()


def test_all_skips_underscore_folders_and_validates_real_cases():
    output = run("--all")
    assert "mini-case" not in output
    assert "the-missing-masterpiece" in output


def test_mermaid(tmp_path):
    assert "graph LR" in run(str(MINI), "--mermaid")


def test_strict_fails_on_warnings(tmp_path):
    case = tmp_path / "mini-case"
    shutil.copytree(MINI, case)
    hints = case / "spoilers" / "hints.yaml"
    hints.write_text(
        hints.read_text().split("- key: why-would-she")[0]
    )  # drop one track → F13 warning
    assert "1 warning" in run(str(case))
    with pytest.raises(CommandError):
        run(str(case), "--strict")


def test_requires_a_path_or_all():
    with pytest.raises(CommandError, match="Give one or more case folders, or --all"):
        run()


def test_unknown_path():
    with pytest.raises(CommandError, match="isn't a folder"):
        run(str(Path("/nonexistent/case")))
