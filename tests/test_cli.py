from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from markcheck.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, relative: str, contents: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_scan_text_output_and_finding_exit_code(self) -> None:
        self.write("README.md", "[Missing](gone.md)\n")
        code, stdout, stderr = self.run_cli("scan", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("[missing-file]", stdout)
        self.assertEqual(stderr, "")

    def test_scan_json_output_is_machine_readable(self) -> None:
        self.write("README.md", "# Valid\n")
        code, stdout, _ = self.run_cli("scan", str(self.root), "--format", "json")
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(payload["finding_count"], 0)
        self.assertEqual(payload["markdown_files"], 1)

    def test_empty_scan_is_informative_and_successful(self) -> None:
        code, stdout, _ = self.run_cli("scan", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("0 Markdown files scanned", stdout)

    def test_links_headings_and_stats_commands(self) -> None:
        readme = self.write("README.md", "# Hello World\n[Guide](guide.md) ![Logo](logo.png)\n")
        links_code, links_output, _ = self.run_cli("links", str(readme))
        headings_code, headings_output, _ = self.run_cli("headings", str(readme))
        stats_code, stats_output, _ = self.run_cli("stats", str(self.root))
        self.assertEqual((links_code, headings_code, stats_code), (0, 0, 0))
        self.assertIn("link [local] guide.md", links_output)
        self.assertIn("H1 Hello World (#hello-world)", headings_output)
        self.assertIn("Links: 1", stats_output)
        self.assertIn("Images: 1", stats_output)

    def test_missing_input_has_execution_failure_exit_code(self) -> None:
        code, _, stderr = self.run_cli("scan", str(self.root / "gone"))
        self.assertEqual(code, 2)
        self.assertIn("error", stderr)

    def test_invalid_arguments_exit_with_code_two(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(("scan",))
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
