"""Content-hashed case assets (docs/ARCHITECTURE.md §7).

The same deterministic function names files at build time (`collect_case_assets`, which copies
them into CASE_ASSETS_DIR for collectstatic) and at import time (`import_case`, which stores
the name), so the database and the deployed files always agree without sharing a disk.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterable
from pathlib import Path

from .loader import read_yaml


def asset_name(case_folder: Path, relative: str, slug: str) -> str:
    """'assets/cover.webp' → 'cases/<slug>/<sha256[:16]>.webp' (path under STATIC_URL)."""
    source = case_folder / relative
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    return f"cases/{slug}/{digest}{source.suffix.lower()}"


def _image_fields(case_folder: Path) -> Iterable[str]:
    case = read_yaml(case_folder / "case.yaml") or {}
    if case.get("cover_image"):
        yield case["cover_image"]
    for file, field in (
        ("people.yaml", "portrait"),
        ("locations.yaml", "image"),
        ("evidence.yaml", "image"),
    ):
        for item in read_yaml(case_folder / file) or []:
            if isinstance(item, dict) and item.get(field):
                yield item[field]


def collect_case_assets(case_folders: Iterable[Path], destination: Path) -> list[Path]:
    """Copy every referenced image of each case to destination/<hashed name>. Idempotent."""
    written: list[Path] = []
    for folder in case_folders:
        slug = (read_yaml(folder / "case.yaml") or {}).get("slug", folder.name)
        for relative in _image_fields(folder):
            target = destination / asset_name(folder, relative, slug)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(folder / relative, target)
            written.append(target)
    return written


def folder_hash(case_folder: Path) -> str:
    """sha256 over every file's relative path and bytes: identical folders hash identically."""
    digest = hashlib.sha256()
    for path in sorted(p for p in case_folder.rglob("*") if p.is_file()):
        digest.update(path.relative_to(case_folder).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
