from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from markcheck.markdown import generate_heading_anchors, parse_markdown


class MarkdownParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, relative: str, contents: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def test_headings_generate_visible_text_anchors_and_duplicates(self) -> None:
        path = self.write(
            "guide.md",
            "# Hello, *World*!\n\n## Hello, **World**!\n\n## API_name\n",
        )
        document = parse_markdown(path)
        self.assertEqual(
            [heading.anchor for heading in document.headings],
            ["hello-world", "hello-world-1", "api_name"],
        )
        self.assertEqual(document.headings[0].text, "Hello, World!")

    def test_anchor_generation_handles_empty_and_unicode_headings(self) -> None:
        self.assertEqual(
            generate_heading_anchors(["!!!", "!!!", "Café déjà vu"]),
            ["", "-1", "café-déjà-vu"],
        )

    def test_reference_style_links_and_images_are_extracted(self) -> None:
        path = self.write(
            "references.md",
            "Read [the guide][guide]. ![Logo][logo]\n\n"
            "[guide]: docs/guide.md\n[logo]: images/logo.png\n",
        )
        document = parse_markdown(path)
        self.assertEqual([link.destination for link in document.links], ["docs/guide.md", "images/logo.png"])
        self.assertFalse(document.links[0].is_image)
        self.assertTrue(document.links[1].is_image)

    def test_fenced_and_inline_code_links_are_ignored(self) -> None:
        path = self.write(
            "code.md",
            "`[inline](missing.md)`\n\n```md\n[fenced](also-missing.md)\n```\n\n[real](ok.md)\n",
        )
        document = parse_markdown(path)
        self.assertEqual([link.destination for link in document.links], ["ok.md"])

    def test_external_links_are_classified_without_network_access(self) -> None:
        path = self.write(
            "external.md",
            "[web](https://example.invalid/x) [mail](mailto:test@example.invalid) "
            "![remote](//cdn.example.invalid/a.png)\n",
        )
        document = parse_markdown(path)
        self.assertTrue(all(link.is_external for link in document.links))


if __name__ == "__main__":
    unittest.main()
