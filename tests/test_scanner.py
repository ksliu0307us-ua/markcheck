from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from markcheck.scanner import ScanError, documentation_stats, read_document, scan_directory


class ScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, relative: str, contents: str = "") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def rules(self) -> list[str]:
        return [finding.rule for finding in scan_directory(self.root).findings]

    def test_valid_and_missing_file_links(self) -> None:
        self.write("README.md", "[Good](docs/guide.md) [Bad](docs/gone.md)\n")
        self.write("docs/guide.md", "# Guide\n")
        result = scan_directory(self.root)
        self.assertEqual([finding.rule for finding in result.findings], ["missing-file"])
        self.assertEqual(result.findings[0].target, "docs/gone.md")

    def test_valid_and_missing_images(self) -> None:
        self.write("README.md", "![Good](images/logo.png) ![Bad](images/gone.png)\n")
        self.write("images/logo.png", "synthetic")
        self.assertEqual(self.rules(), ["missing-image"])

    def test_relative_space_percent_encoded_query_and_fragment_paths(self) -> None:
        self.write(
            "docs/index.md",
            "[Raw](../files/a file.md?download=1#setup) "
            "[Encoded](../files/a%20file.md#setup)\n",
        )
        self.write("files/a file.md", "# Setup\n")
        self.assertEqual(self.rules(), [])

    def test_same_and_cross_document_fragments(self) -> None:
        self.write(
            "README.md",
            "# Usage\n[Same](#usage) [Other](guide.md#install) "
            "[Missing](guide.md#gone)\n",
        )
        self.write("guide.md", "# Install\n")
        result = scan_directory(self.root)
        self.assertEqual([finding.rule for finding in result.findings], ["missing-fragment"])

    def test_duplicate_heading_fragments(self) -> None:
        self.write("README.md", "# Repeat\n# Repeat\n[Second](#repeat-1)\n")
        self.assertEqual(self.rules(), [])

    def test_heading_level_skip_is_reported_at_heading_line(self) -> None:
        self.write("README.md", "# One\n\n## Two\n\n#### Four\n")
        result = scan_directory(self.root)
        self.assertEqual(result.findings[0].rule, "heading-level-skip")
        self.assertEqual(result.findings[0].line, 5)

    def test_external_urls_are_skipped(self) -> None:
        self.write(
            "README.md",
            "[Web](https://example.invalid/missing) [FTP](ftp://example.invalid/a)\n",
        )
        with patch("socket.create_connection", side_effect=AssertionError("network attempted")):
            self.assertEqual(self.rules(), [])

    def test_exclusion_patterns_and_default_directories(self) -> None:
        self.write("README.md", "# Good\n")
        self.write("ignored/bad.md", "[Bad](missing.md)\n")
        self.write(".venv/bad.md", "[Bad](missing.md)\n")
        result = scan_directory(self.root, ["ignored/**"])
        self.assertEqual(result.findings, [])
        self.assertEqual(len(result.documents), 1)

    def test_root_relative_links_use_scan_root(self) -> None:
        self.write("docs/guide.md", "[Home](/README.md)\n")
        self.write("README.md", "# Home\n")
        self.assertEqual(self.rules(), [])

    def test_parent_link_outside_root_is_rejected(self) -> None:
        outside = self.root.parent / "outside-markcheck-test.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        self.write("README.md", f"[Outside](../{outside.name})\n")
        self.assertEqual(self.rules(), ["target-outside-root"])

    def test_symlink_target_outside_root_is_rejected_where_supported(self) -> None:
        outside_directory = self.root.parent / f"{self.root.name}-outside"
        outside_directory.mkdir()
        self.addCleanup(lambda: outside_directory.rmdir())
        (outside_directory / "secret.md").write_text("# Secret\n", encoding="utf-8")
        self.addCleanup(lambda: (outside_directory / "secret.md").unlink(missing_ok=True))
        link = self.root / "linked"
        try:
            os.symlink(outside_directory, link, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlinks unavailable: {error}")
        self.write("README.md", "[Secret](linked/secret.md)\n")
        self.assertEqual(self.rules(), ["target-outside-root"])

    def test_empty_directory_has_zero_stats_and_no_findings(self) -> None:
        self.assertEqual(scan_directory(self.root).findings, [])
        stats = documentation_stats(self.root)
        self.assertEqual(stats.to_dict(), {"markdown_files": 0, "headings": 0, "links": 0, "images": 0})

    def test_nonexistent_and_non_directory_inputs_fail(self) -> None:
        with self.assertRaises(ScanError):
            scan_directory(self.root / "gone")
        file_path = self.write("README.md", "# Readme\n")
        with self.assertRaises(ScanError):
            scan_directory(file_path)

    def test_unreadable_input_is_reported(self) -> None:
        path = self.write("README.md", "# Readme\n")
        with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
            with self.assertRaises(ScanError):
                read_document(path)

    def test_findings_are_deterministic(self) -> None:
        self.write("z.md", "[Z](missing-z.md)\n")
        self.write("a.md", "[A](missing-a.md)\n")
        first = [finding.to_dict() for finding in scan_directory(self.root).findings]
        second = [finding.to_dict() for finding in scan_directory(self.root).findings]
        self.assertEqual(first, second)
        self.assertEqual([item["source"] for item in first], ["a.md", "z.md"])

    def test_scan_does_not_modify_documents(self) -> None:
        path = self.write("README.md", "# Original\n[Missing](gone.md)\n")
        before = path.read_bytes()
        scan_directory(self.root)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
