"""Validate case folders against the authoring format and fairness rules.

manage.py validate_case ../content/cases/the-missing-masterpiece
manage.py validate_case --all              # every case not starting with "_"
manage.py validate_case <path> --mermaid   # also print the unlock graph (Mermaid)
manage.py validate_case --all --strict     # warnings fail too
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.validator import validate_case

CASES_DIR = settings.REPO_ROOT / "content" / "cases"


class Command(BaseCommand):
    help = "Validate case folders (docs/CASE_DESIGN.md §8)."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", help="case folder(s)")
        parser.add_argument("--all", action="store_true", help="every case under content/cases")
        parser.add_argument("--mermaid", action="store_true", help="print the unlock graph")
        parser.add_argument("--strict", action="store_true", help="treat warnings as errors")

    def handle(self, *args, paths, all, mermaid, strict, **options):
        folders = [Path(p) for p in paths]
        if all:
            folders += sorted(
                p for p in CASES_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")
            )
        if not folders:
            raise CommandError("Give one or more case folders, or --all.")

        failed = 0
        for folder in folders:
            if not folder.is_dir():
                raise CommandError(f"{folder} isn't a folder.")
            report = validate_case(folder, mermaid=mermaid)
            n_err, n_warn = len(report.errors), len(report.warnings)
            warn_text = f"{n_warn} warning{'s' if n_warn != 1 else ''}"
            if report.ok and not (strict and n_warn):
                self.stdout.write(self.style.SUCCESS(f"✓ {report.case}: valid ({warn_text})"))
            else:
                failed += 1
                summary = f"{n_err} error{'s' if n_err != 1 else ''}, {warn_text}"
                self.stdout.write(self.style.ERROR(f"✗ {report.case}: {summary}"))
            for issue in report.issues:
                self.stdout.write(f"  {issue}")
            if mermaid and report.mermaid:
                self.stdout.write(report.mermaid)

        if failed:
            noun = "case has" if failed == 1 else "cases have"
            raise CommandError(f"{failed} {noun} errors.")
