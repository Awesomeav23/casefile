"""Copy case images to CASE_ASSETS_DIR under content-hashed names (run before collectstatic).

manage.py collect_case_assets                       # every real case
manage.py collect_case_assets --include-fixtures    # also content/cases/_fixtures/*
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from content.assets import collect_case_assets


class Command(BaseCommand):
    help = "Copy case images to the static source folder under content-hashed names."

    def add_arguments(self, parser):
        parser.add_argument("--include-fixtures", action="store_true")

    def handle(self, *args, include_fixtures, **options):
        cases_dir = settings.CASES_DIR
        folders = [p for p in cases_dir.iterdir() if p.is_dir() and not p.name.startswith("_")]
        if include_fixtures and (cases_dir / "_fixtures").is_dir():
            folders += [p for p in (cases_dir / "_fixtures").iterdir() if p.is_dir()]
        written = collect_case_assets(sorted(folders), settings.CASE_ASSETS_DIR)
        self.stdout.write(f"Collected {len(written)} asset(s) into {settings.CASE_ASSETS_DIR}")
