"""Import validated case folders into the database (docs/CASE_DESIGN.md §8).

manage.py import_case ../content/cases/the-missing-masterpiece           # import as draft
manage.py import_case ../content/cases/the-missing-masterpiece --publish
manage.py import_case --all                                              # every real case
manage.py import_case <path> --force    # allow breaking changes to a published case
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.importer import ImportRefused, import_case


class Command(BaseCommand):
    help = "Validate and import case folders (upsert by key; refuses on validation errors)."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", help="case folder(s)")
        parser.add_argument("--all", action="store_true", help="every case under content/cases")
        parser.add_argument("--publish", action="store_true", help="publish after importing")
        parser.add_argument(
            "--force", action="store_true", help="allow breaking changes to a published case"
        )

    def handle(self, *args, paths, all, publish, force, **options):
        folders = [Path(p) for p in paths]
        if all:
            folders += sorted(
                p for p in settings.CASES_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")
            )
        if not folders:
            raise CommandError("Give one or more case folders, or --all.")

        refused: list[ImportRefused] = []
        for folder in folders:
            if not folder.is_dir():
                raise CommandError(f"{folder} isn't a folder.")
            try:
                r = import_case(folder, publish=publish, force=force)
            except ImportRefused as exc:
                refused.append(exc)
                self.stdout.write(self.style.ERROR(f"✗ {exc.slug}: refused"))
                for reason in exc.reasons:
                    self.stdout.write(f"  {reason}")
                continue
            if r.action == "unchanged":
                self.stdout.write(
                    f"= {r.slug}: unchanged ({r.status}, version {r.content_version})"
                )
            else:
                extra = ", breaking" if r.breaking else ""
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {r.slug}: {r.action} ({r.status}, version {r.content_version}{extra})"
                    )
                )
            for warning in r.warnings:
                self.stdout.write(f"  {warning}")

        if refused:
            noun = "case was" if len(refused) == 1 else "cases were"
            raise CommandError(f"{len(refused)} {noun} refused.")
