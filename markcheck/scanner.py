"""Markdown discovery, path resolution, and validation."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .markdown import parse_markdown
from .models import Document, DocumentationStats, Finding, ScanResult


DEFAULT_EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "env",
    "htmlcov",
    "node_modules",
    "venv",
    "vendor",
}
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}


class ScanError(Exception):
    """An input or execution failure that should result in exit code 2."""


def _matches_exclusion(relative: str, patterns: list[str], *, is_dir: bool) -> bool:
    normalized = relative.replace("\\", "/").lstrip("./")
    candidates = [normalized]
    if is_dir:
        candidates.append(f"{normalized}/")
    return any(
        fnmatch.fnmatchcase(candidate, pattern.replace("\\", "/").lstrip("./"))
        for pattern in patterns
        for candidate in candidates
    )


def discover_markdown_files(root: Path, excludes: list[str] | None = None) -> list[Path]:
    """Find Markdown files below root without following directory symlinks."""

    excludes = excludes or []
    if not root.exists():
        raise ScanError(f"input does not exist: {root}")
    if not root.is_dir():
        raise ScanError(f"input is not a directory: {root}")
    try:
        root = root.resolve(strict=True)
        files: list[Path] = []
        for current, directory_names, file_names in os.walk(root, followlinks=False):
            current_path = Path(current)
            kept_directories: list[str] = []
            for name in sorted(directory_names):
                candidate = current_path / name
                relative = candidate.relative_to(root).as_posix()
                if name in DEFAULT_EXCLUDED_DIRECTORIES:
                    continue
                if candidate.is_symlink():
                    continue
                if _matches_exclusion(relative, excludes, is_dir=True):
                    continue
                kept_directories.append(name)
            directory_names[:] = kept_directories
            for name in sorted(file_names):
                candidate = current_path / name
                if candidate.suffix.casefold() not in MARKDOWN_SUFFIXES:
                    continue
                relative = candidate.relative_to(root).as_posix()
                if _matches_exclusion(relative, excludes, is_dir=False):
                    continue
                files.append(candidate)
        return sorted(files, key=lambda item: item.relative_to(root).as_posix())
    except OSError as error:
        raise ScanError(f"cannot read input directory {root}: {error}") from error


def read_document(path: Path) -> Document:
    """Parse one readable Markdown file or raise a user-facing ScanError."""

    if not path.exists():
        raise ScanError(f"input does not exist: {path}")
    if not path.is_file():
        raise ScanError(f"input is not a file: {path}")
    try:
        return parse_markdown(path.resolve(strict=True))
    except (OSError, UnicodeError) as error:
        raise ScanError(f"cannot read Markdown file {path}: {error}") from error


def _source_name(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _finding(
    document: Document,
    root: Path,
    line: int,
    rule: str,
    message: str,
    target: str | None = None,
) -> Finding:
    return Finding(
        source=_source_name(document.path, root),
        line=line,
        rule=rule,
        message=message,
        target=target,
    )


def _resolve_target(document: Document, destination: str, root: Path) -> tuple[Path, str]:
    parsed = urlsplit(destination)
    decoded_path = unquote(parsed.path)
    fragment = unquote(parsed.fragment)
    if not decoded_path:
        target = document.path
    elif decoded_path.startswith("/"):
        target = root / decoded_path.lstrip("/")
    else:
        target = document.path.parent / decoded_path
    try:
        resolved = target.resolve(strict=False)
    except OSError as error:
        raise ScanError(f"cannot resolve target {destination!r}: {error}") from error
    return resolved, fragment


def _within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _heading_findings(document: Document, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    previous_level: int | None = None
    for heading in document.headings:
        if previous_level is not None and heading.level > previous_level + 1:
            findings.append(
                _finding(
                    document,
                    root,
                    heading.line,
                    "heading-level-skip",
                    f"heading level jumps from H{previous_level} to H{heading.level}",
                )
            )
        previous_level = heading.level
    return findings


def scan_directory(root: Path, excludes: list[str] | None = None) -> ScanResult:
    """Scan all Markdown documents below root and return ordered findings."""

    root = root.resolve(strict=False)
    paths = discover_markdown_files(root, excludes)
    documents: list[Document] = []
    for path in paths:
        try:
            documents.append(parse_markdown(path))
        except (OSError, UnicodeError) as error:
            raise ScanError(f"cannot read Markdown file {path}: {error}") from error

    document_cache = {document.path.resolve(): document for document in documents}
    findings: list[Finding] = []
    for document in documents:
        findings.extend(_heading_findings(document, root))
        for link in document.links:
            if link.is_external:
                continue
            target_path, fragment = _resolve_target(document, link.destination, root)
            if not _within_root(target_path, root):
                findings.append(
                    _finding(
                        document,
                        root,
                        link.line,
                        "target-outside-root",
                        "local target resolves outside the scan root",
                        link.destination,
                    )
                )
                continue
            if not target_path.exists():
                kind = "image" if link.is_image else "file"
                findings.append(
                    _finding(
                        document,
                        root,
                        link.line,
                        f"missing-{kind}",
                        f"local {kind} target does not exist",
                        link.destination,
                    )
                )
                continue
            if fragment and not link.is_image and target_path.is_file():
                if target_path.suffix.casefold() not in MARKDOWN_SUFFIXES:
                    continue
                target_document = document_cache.get(target_path.resolve())
                if target_document is None:
                    try:
                        target_document = parse_markdown(target_path)
                        document_cache[target_path.resolve()] = target_document
                    except (OSError, UnicodeError) as error:
                        raise ScanError(f"cannot read Markdown target {target_path}: {error}") from error
                if fragment not in {heading.anchor for heading in target_document.headings}:
                    findings.append(
                        _finding(
                            document,
                            root,
                            link.line,
                            "missing-fragment",
                            f"heading fragment #{fragment} does not exist in target document",
                            link.destination,
                        )
                    )

    result = ScanResult(root=root, documents=documents, findings=findings)
    result.findings = result.sorted_findings()
    return result


def documentation_stats(root: Path, excludes: list[str] | None = None) -> DocumentationStats:
    """Count documents, headings, links, and images below root."""

    paths = discover_markdown_files(root.resolve(strict=False), excludes)
    documents: list[Document] = []
    for path in paths:
        try:
            documents.append(parse_markdown(path))
        except (OSError, UnicodeError) as error:
            raise ScanError(f"cannot read Markdown file {path}: {error}") from error
    return DocumentationStats(
        markdown_files=len(documents),
        headings=sum(len(document.headings) for document in documents),
        links=sum(sum(not link.is_image for link in document.links) for document in documents),
        images=sum(sum(link.is_image for link in document.links) for document in documents),
    )
