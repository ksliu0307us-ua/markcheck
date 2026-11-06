# MarkCheck

MarkCheck is an offline command-line checker for Markdown documentation. It is
intended for maintainers, technical writers, and developers who want fast,
repeatable checks without uploading documentation or making network requests.
It is written for Python 3.11 or later and uses
[`markdown-it-py`](https://github.com/executablebooks/markdown-it-py) for
structured CommonMark parsing.

This repository is a new, original, AI-assisted implementation built from
synthetic examples. MarkCheck never edits the documents it checks.

## Features

- Finds links to missing local files and images.
- Validates same-document and cross-document heading fragments.
- Detects skipped heading levels, such as H2 followed by H4.
- Handles inline links, reference-style links, images, queries, fragments, and
  percent-encoded local paths.
- Lists links, images, headings, and generated heading anchors.
- Summarizes Markdown file, heading, link, and image counts.
- Produces readable text and deterministic JSON scan reports.
- Skips external URLs entirely; no network access is attempted.
- Enforces the scan root and avoids traversing symlinked directories.

## Installation

Create and activate a virtual environment, then install MarkCheck:

```console
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

On macOS or Linux, activate with `source .venv/bin/activate`. The editable
install provides both the `markcheck` command and `python -m markcheck`.

## Commands

Scan a documentation tree and print a text report:

```console
python -m markcheck scan ./docs
```

Request machine-readable JSON:

```console
python -m markcheck scan ./docs --format json
```

Exclude one or more project-relative globs:

```console
python -m markcheck scan . --exclude "examples/broken/**"
python -m markcheck scan . --exclude "drafts/**" --exclude "archive/*.md"
```

List links and images, list headings, or summarize a tree:

```console
python -m markcheck links ./README.md
python -m markcheck headings ./README.md
python -m markcheck stats ./docs
```

The `links`, `headings`, and `stats` commands also accept `--format json`.
After installation, replace `python -m markcheck` in any example with
`markcheck`.

## Reports

A text finding includes the source file, containing block's starting line,
rule identifier, explanation, and target when applicable:

```text
Found 1 documentation problem:
README.md:8: [missing-file] local file target does not exist (target: guide/missing.md)
```

`markdown-it-py` does not expose exact source columns for every inline token,
so MarkCheck reports the start line of the containing paragraph, list item, or
heading. Output order is deterministic: source path, line, rule, target, then
message.

The equivalent JSON report has a stable object shape:

```json
{
  "finding_count": 1,
  "findings": [
    {
      "line": 8,
      "message": "local file target does not exist",
      "rule": "missing-file",
      "source": "README.md",
      "target": "guide/missing.md"
    }
  ],
  "markdown_files": 1,
  "root": "C:\\path\\to\\project"
}
```

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | The operation completed successfully and a scan found no problems. |
| 1 | A completed scan found one or more documentation problems. |
| 2 | Arguments were invalid, input was unreadable, or execution failed. |

An empty but readable directory succeeds and reports that zero Markdown files
were scanned.

## Paths, exclusions, and the project root

The directory passed to `scan` is the project root. Relative destinations are
resolved from the source document's directory. A destination beginning with
`/` is resolved from the project root, not the filesystem root. Query strings
and fragments are separated before percent-decoding and resolving the path.

Targets that resolve outside the root are reported as `target-outside-root`.
Directory symlinks are not traversed during discovery, and a linked target that
resolves outside the root is rejected. MarkCheck excludes common metadata,
virtual-environment, dependency, cache, and build directories by default,
including `.git`, `.venv`, `venv`, `node_modules`, `vendor`, `build`, and
`dist`. User `--exclude` globs use forward-slash, project-relative paths and
may be repeated.

External destinations, including `https:`, `mailto:`, and protocol-relative
URLs, are identified by syntax and skipped without a request.

## Heading anchors

MarkCheck derives anchors from the visible heading text as follows:

1. Trim whitespace and Unicode-case-fold the text.
2. Keep Unicode letters and numbers, whitespace, hyphens, and underscores.
3. Collapse whitespace and consecutive hyphens to one hyphen.
4. Remove leading and trailing hyphens.
5. Give repeated anchors suffixes `-1`, `-2`, and so on in document order.

For example, two headings named `Quick Start!` produce `quick-start` and
`quick-start-1`. This algorithm is deterministic but does not claim complete
GitHub compatibility.

MarkCheck v0.1.0 uses CommonMark tokens. Raw HTML links, explicit HTML anchors,
setext-specific platform quirks, and anchors generated by unusual Markdown
extensions are outside its current scope. Fragments on non-Markdown files are
not validated.

## Examples

[`examples/valid`](examples/valid/) is a small documentation tree that should
pass:

```console
python -m markcheck scan examples/valid
```

[`examples/broken`](examples/broken/) intentionally contains missing targets,
an invalid fragment, and a heading-level skip. Its scan is expected to report
findings and return exit code `1`:

```console
python -m markcheck scan examples/broken
```

When scanning this repository itself, exclude the intentionally broken tree:

```console
python -m markcheck scan . --exclude "examples/broken/**"
```

## Tests

The tests use only temporary directories and synthetic records:

```console
python -m unittest discover -s tests -v
```

## Roadmap and license

Proposed work is listed in the [roadmap](ROADMAP.md). MarkCheck is available
under the [MIT License](LICENSE).
