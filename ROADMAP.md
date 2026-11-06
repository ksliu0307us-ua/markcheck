# MarkCheck roadmap

The following items are proposed and unimplemented. Estimates total **31
hours** and describe work beyond version 0.1.0.

## Project configuration file — 4 hours

Support a `markcheck.toml` file for default scan roots, exclusion patterns, and
rule selection.

Acceptance criteria:

- Configuration is discovered predictably and can be overridden by CLI flags.
- Invalid keys and values produce actionable errors and exit code 2.
- Unit tests cover discovery, precedence, and invalid configurations.

## Additional anchor conventions — 4 hours

Add opt-in anchor strategies for widely used documentation platforms while
keeping the current deterministic strategy as the default.

Acceptance criteria:

- At least two named strategies have documented algorithms and fixtures.
- Duplicate, punctuation, Unicode, and empty headings are covered by tests.
- Reports identify which strategy was used.

## Incremental scan cache — 5 hours

Cache parsed document metadata so unchanged trees can be checked faster.

Acceptance criteria:

- Cache keys incorporate file content and relevant configuration.
- Changed, removed, and renamed documents invalidate the right entries.
- Corrupt or incompatible caches fall back safely to a full scan.
- Benchmarks demonstrate reduced work on an unchanged synthetic tree.

## Watch mode — 4 hours

Provide a long-running local mode that rescans documentation after filesystem
changes.

Acceptance criteria:

- Changes are debounced and results remain deterministically ordered.
- Create, modify, rename, and delete events are handled.
- Interrupting the process exits cleanly without leaving temporary files.

## Pre-commit integration — 3 hours

Publish a documented pre-commit hook that checks staged documentation.

Acceptance criteria:

- A sample `.pre-commit-config.yaml` works in a clean fixture repository.
- The hook returns the standard MarkCheck exit codes.
- Documentation explains full-tree and changed-file workflows.

## Editor integration — 6 hours

Create a Language Server Protocol adapter that exposes findings as editor
diagnostics.

Acceptance criteria:

- Opening and changing a Markdown document updates diagnostics.
- Diagnostic ranges follow MarkCheck's documented block-line precision.
- Workspace root and exclusion behavior matches the CLI.
- Setup is documented for at least one editor and covered by protocol tests.

## SARIF and CI reporting — 3 hours

Add SARIF output and ready-to-copy continuous-integration examples.

Acceptance criteria:

- Findings map to valid SARIF locations, rules, and messages.
- Generated SARIF passes a schema validator in automated tests.
- Documentation includes a minimal GitHub Actions workflow.

## Focused repair suggestions — 2 hours

Suggest likely local targets for missing links without modifying source files.

Acceptance criteria:

- Suggestions are limited to unambiguous, in-root candidates.
- Ranking and tie behavior are deterministic and tested.
- Text and JSON reports clearly distinguish suggestions from applied fixes.
