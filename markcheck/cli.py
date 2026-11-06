"""Command-line interface for MarkCheck."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .models import Document, DocumentationStats, ScanResult
from .scanner import ScanError, documentation_stats, read_document, scan_directory


def _add_format_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="report format (default: text)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markcheck",
        description="Check Markdown documentation locally without network requests.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)

    scan_parser = commands.add_parser("scan", help="recursively check Markdown files")
    scan_parser.add_argument("path", type=Path, help="documentation directory to scan")
    scan_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="exclude a project-relative glob (repeatable)",
    )
    _add_format_option(scan_parser)

    links_parser = commands.add_parser("links", help="list links and images in one file")
    links_parser.add_argument("path", type=Path, help="Markdown file to inspect")
    _add_format_option(links_parser)

    headings_parser = commands.add_parser("headings", help="list headings and anchors in one file")
    headings_parser.add_argument("path", type=Path, help="Markdown file to inspect")
    _add_format_option(headings_parser)

    stats_parser = commands.add_parser("stats", help="summarize a Markdown directory")
    stats_parser.add_argument("path", type=Path, help="documentation directory to summarize")
    stats_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="exclude a project-relative glob (repeatable)",
    )
    _add_format_option(stats_parser)
    return parser


def _write_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _render_scan(result: ScanResult, output_format: str) -> None:
    if output_format == "json":
        _write_json(
            {
                "root": str(result.root),
                "markdown_files": len(result.documents),
                "finding_count": len(result.findings),
                "findings": [finding.to_dict() for finding in result.findings],
            }
        )
        return
    if not result.findings:
        count = len(result.documents)
        noun = "file" if count == 1 else "files"
        print(f"No problems found ({count} Markdown {noun} scanned).")
        return
    count = len(result.findings)
    noun = "problem" if count == 1 else "problems"
    print(f"Found {count} documentation {noun}:")
    for finding in result.findings:
        target = f" (target: {finding.target})" if finding.target is not None else ""
        print(f"{finding.source}:{finding.line}: [{finding.rule}] {finding.message}{target}")


def _document_payload(document: Document) -> dict[str, Any]:
    return {"file": str(document.path)}


def _render_links(document: Document, output_format: str) -> None:
    if output_format == "json":
        payload = _document_payload(document)
        payload["links"] = [link.to_dict() for link in document.links]
        _write_json(payload)
        return
    if not document.links:
        print(f"No links or images found in {document.path}.")
        return
    for link in document.links:
        kind = "image" if link.is_image else "link"
        location = "external" if link.is_external else "local"
        label = f" — {link.label}" if link.label else ""
        print(f"{link.line}: {kind} [{location}] {link.destination}{label}")


def _render_headings(document: Document, output_format: str) -> None:
    if output_format == "json":
        payload = _document_payload(document)
        payload["headings"] = [heading.to_dict() for heading in document.headings]
        _write_json(payload)
        return
    if not document.headings:
        print(f"No headings found in {document.path}.")
        return
    for heading in document.headings:
        print(f"{heading.line}: H{heading.level} {heading.text} (#{heading.anchor})")


def _render_stats(stats: DocumentationStats, output_format: str) -> None:
    if output_format == "json":
        _write_json(stats.to_dict())
        return
    print(f"Markdown files: {stats.markdown_files}")
    print(f"Headings: {stats.headings}")
    print(f"Links: {stats.links}")
    print(f"Images: {stats.images}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run MarkCheck and return its documented process exit code."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "scan":
            result = scan_directory(arguments.path, arguments.exclude)
            _render_scan(result, arguments.format)
            return 1 if result.findings else 0
        if arguments.command == "links":
            _render_links(read_document(arguments.path), arguments.format)
            return 0
        if arguments.command == "headings":
            _render_headings(read_document(arguments.path), arguments.format)
            return 0
        if arguments.command == "stats":
            _render_stats(documentation_stats(arguments.path, arguments.exclude), arguments.format)
            return 0
    except ScanError as error:
        print(f"markcheck: error: {error}", file=sys.stderr)
        return 2
    parser.error(f"unknown command: {arguments.command}")
    return 2
