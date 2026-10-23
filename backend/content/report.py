"""Validation issues and the report the validator returns."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    rule: str  # e.g. "schema", "reference", "F1"
    file: str  # path inside the case folder, e.g. "evidence.yaml"
    key: str | None  # the item key (or path) the issue is about
    message: str

    def __str__(self) -> str:
        where = f"{self.file} › {self.key}" if self.key else self.file
        return f"[{self.level}] {self.rule}: {where}: {self.message}"


@dataclass
class Report:
    case: str
    issues: list[Issue] = field(default_factory=list)
    mermaid: str | None = None

    def error(self, rule: str, file: str, key: str | None, message: str) -> None:
        self.issues.append(Issue("error", rule, file, key, message))

    def warning(self, rule: str, file: str, key: str | None, message: str) -> None:
        self.issues.append(Issue("warning", rule, file, key, message))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def rules(self, level: str | None = None) -> set[str]:
        return {i.rule for i in self.issues if level is None or i.level == level}
