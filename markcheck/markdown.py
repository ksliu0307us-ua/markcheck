"""Markdown token extraction and deterministic heading anchors."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .models import Document, Heading, Link


_SPACE_OR_HYPHEN = re.compile(r"[\s-]+", re.UNICODE)


def is_external_destination(destination: str) -> bool:
    """Return whether a destination is not a local filesystem reference."""

    if destination.startswith("//"):
        return True
    return bool(urlsplit(destination).scheme)


def _anchor_base(text: str) -> str:
    """Create the non-deduplicated MarkCheck anchor for heading text."""

    normalized = text.strip().casefold()
    normalized = "".join(
        character
        for character in normalized
        if character.isalnum() or character in {" ", "\t", "\n", "-", "_"}
    )
    return _SPACE_OR_HYPHEN.sub("-", normalized).strip("-")


def generate_heading_anchors(texts: list[str]) -> list[str]:
    """Generate deterministic anchors, suffixing duplicate bases from ``-1``."""

    counts: dict[str, int] = defaultdict(int)
    anchors: list[str] = []
    for text in texts:
        base = _anchor_base(text)
        count = counts[base]
        anchors.append(base if count == 0 else f"{base}-{count}")
        counts[base] += 1
    return anchors


def _attribute(token: Token, name: str) -> str:
    value = token.attrGet(name)
    return value if value is not None else ""


def _label_for_link(children: list[Token], start: int) -> str:
    parts: list[str] = []
    depth = 0
    for child in children[start + 1 :]:
        if child.type == "link_open":
            depth += 1
        elif child.type == "link_close":
            if depth == 0:
                break
            depth -= 1
        elif child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
        elif child.type == "image":
            parts.append(child.content)
    return "".join(parts).strip()


def _inline_text(token: Token) -> str:
    """Return visible text represented by an inline token."""

    if not token.children:
        return token.content.strip()
    parts: list[str] = []
    for child in token.children:
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type == "image":
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts).strip()


def parse_markdown(path: Path) -> Document:
    """Read and parse one UTF-8 Markdown document using structured tokens."""

    source = path.read_text(encoding="utf-8")
    tokens = MarkdownIt("commonmark").parse(source)
    heading_rows: list[tuple[int, str, int]] = []
    links: list[Link] = []

    for index, token in enumerate(tokens):
        line = (token.map[0] + 1) if token.map else 1
        if token.type == "heading_open" and index + 1 < len(tokens):
            inline = tokens[index + 1]
            if inline.type == "inline":
                level = int(token.tag[1:])
                heading_rows.append((level, _inline_text(inline), line))

        if token.type != "inline" or not token.children:
            continue
        for child_index, child in enumerate(token.children):
            if child.type == "link_open":
                destination = _attribute(child, "href")
                links.append(
                    Link(
                        destination=destination,
                        line=line,
                        is_external=is_external_destination(destination),
                        label=_label_for_link(token.children, child_index),
                    )
                )
            elif child.type == "image":
                destination = _attribute(child, "src")
                links.append(
                    Link(
                        destination=destination,
                        line=line,
                        is_image=True,
                        is_external=is_external_destination(destination),
                        label=child.content,
                    )
                )

    anchors = generate_heading_anchors([row[1] for row in heading_rows])
    headings = [
        Heading(level=level, text=text, anchor=anchor, line=line)
        for (level, text, line), anchor in zip(heading_rows, anchors, strict=True)
    ]
    return Document(path=path, headings=headings, links=links)
