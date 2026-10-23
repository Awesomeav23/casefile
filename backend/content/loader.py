"""Read a case folder into a CaseBundle, reporting problems by file and item key."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from .report import Report
from .schema import FILES, CaseBundle


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (plain PyYAML keeps the last one)."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False):
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=_UniqueKeyLoader)  # noqa: S506 (SafeLoader subclass)


def _readable_path(raw: Any, loc: tuple[Any, ...]) -> str:
    """('topics', 0, 'statements', 1, 'text') → 'topics[her-talk].statements[at-lectern].text'."""
    parts: list[str] = []
    node = raw
    for part in loc:
        if isinstance(part, int):
            item = node[part] if isinstance(node, list) and part < len(node) else None
            label = item.get("key") if isinstance(item, dict) else None
            parts[-1:] = [f"{parts[-1] if parts else ''}[{label or f'#{part + 1}'}]"]
            node = item
        else:
            name = "from" if part == "from_" else str(part)
            parts.append(name)
            node = node.get(name) if isinstance(node, dict) else None
    return ".".join(parts) or "(root)"


def _validate(
    model: type[BaseModel], raw: Any, report: Report, file: str, key: str | None
) -> BaseModel | None:
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        for err in exc.errors():
            path = _readable_path(raw, tuple(err["loc"]))
            message = err["msg"].removeprefix("Value error, ")
            report.error("schema", file, key, f"{path}: {message}")
        return None


def load_case(folder: Path) -> tuple[CaseBundle | None, Report]:
    report = Report(case=folder.name)
    parsed: dict[str, Any] = {}

    for file, (field, model, shape) in FILES.items():
        path = folder / file
        if not path.is_file():
            report.error("missing-file", file, None, "required file is missing")
            continue
        try:
            raw = read_yaml(path)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
            where = f" (line {mark.line + 1})" if mark else ""
            problem = getattr(exc, "problem", None) or str(exc)
            report.error("yaml", file, None, f"invalid YAML{where}: {problem}")
            continue

        if shape == "object":
            if not isinstance(raw, dict):
                report.error("schema", file, None, "the file must contain a mapping")
                continue
            parsed[field] = _validate(model, raw, report, file, None)
        elif shape == "list":
            raw = [] if raw is None else raw
            if not isinstance(raw, list):
                report.error("schema", file, None, "the file must contain a list")
                continue
            items, seen = [], set()
            for index, entry in enumerate(raw):
                key = entry.get("key") if isinstance(entry, dict) else None
                label = key if isinstance(key, str) else f"#{index + 1}"
                if isinstance(key, str):
                    if key in seen:
                        report.error("duplicate-key", file, key, "key is used more than once")
                    seen.add(key)
                items.append(_validate(model, entry, report, file, label))
            parsed[field] = items
        else:  # mapping of person key → interview
            raw = {} if raw is None else raw
            if not isinstance(raw, dict):
                report.error("schema", file, None, "the file must map person keys to interviews")
                continue
            parsed[field] = {
                str(k): _validate(model, v or {}, report, file, str(k)) for k, v in raw.items()
            }

    if not report.ok:
        return None, report
    return CaseBundle(**parsed), report
