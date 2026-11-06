"""Data models shared by MarkCheck's parser, scanner, and CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Link:
    """A link or image extracted from a Markdown document."""

    destination: str
    line: int
    is_image: bool = False
    is_external: bool = False
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Heading:
    """A Markdown heading and its generated anchor."""

    level: int
    text: str
    anchor: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Document:
    """Structured information extracted from one Markdown document."""

    path: Path
    headings: list[Heading] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    """A documentation problem reported by a scan."""

    source: str
    line: int
    rule: str
    message: str
    target: str | None = None

    def sort_key(self) -> tuple[str, int, str, str, str]:
        return (self.source, self.line, self.rule, self.target or "", self.message)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.target is None:
            data.pop("target")
        return data


@dataclass
class ScanResult:
    """The documents and findings produced by a scan."""

    root: Path
    documents: list[Document] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def sorted_findings(self) -> list[Finding]:
        return sorted(self.findings, key=Finding.sort_key)


@dataclass(frozen=True)
class DocumentationStats:
    markdown_files: int
    headings: int
    links: int
    images: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)
