#!/usr/bin/env python3
import csv
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import generate_report
from email_brand import FONT_STACK, LOGO_CID

HEADER = generate_report.EXPECTED_COLUMNS
SAMPLE = {
    "id": "1",
    "inicio_local": "2026-11-23 09:00",
    "fin_local": "2026-11-23 09:20",
    "motivo": "Reunión de prueba 01",
    "estado": "approved",
}


class HtmlStructureChecker(HTMLParser):
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.images = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            self.images.append(attrs)
        if tag == "a":
            self.links.append(attrs)
        if tag not in self.VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("</{}> inesperado".format(tag))
            return
        self.stack.pop()


class GenerateReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_csv(self, rows, header=HEADER):
        path = self.base / "report.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_csv_with_reservations(self):
        path = self.write_csv([SAMPLE])
        rows = generate_report.read_rows(path)
        output = generate_report.render(rows, "2026-11-23 a 2026-11-30", "America/Mexico_City")
        self.assertIn("Se registró 1 reserva", output)
        self.assertIn("Reunión de prueba 01", output)
        self.assertIn("approved", output)
        self.assertIn("2026-11-23 09:00", output)
        self.assertIn("<thead>", output)
        self.assertNotIn("<script", output)

    def test_empty_csv(self):
        path = self.write_csv([])
        rows = generate_report.read_rows(path)
        output = generate_report.render(rows, "periodo", "America/Mexico_City")
        self.assertIn("No hay reservas en el periodo solicitado.", output)
        self.assertNotIn("<thead>", output)

    def test_html_special_characters_are_escaped(self):
        hostile = dict(SAMPLE, motivo='<script>alert("x") & y</script>', estado="<b>approved</b>")
        path = self.write_csv([hostile])
        rows = generate_report.read_rows(path)
        output = generate_report.render(rows, '<periodo>&', "America/Mexico_City")
        self.assertIn("&lt;script&gt;", output)
        self.assertIn("&amp;", output)
        self.assertIn("&quot;", output)
        self.assertNotIn("<script>", output)
        self.assertNotIn("<b>approved</b>", output)
        self.assertIn("&lt;periodo&gt;&amp;", output)

    def test_missing_column(self):
        path = self.write_csv([], header=HEADER[:-1])
        with self.assertRaises(ValueError):
            generate_report.read_rows(path)

    def test_unexpected_column(self):
        path = self.write_csv([], header=HEADER + ["extra"])
        with self.assertRaises(ValueError):
            generate_report.read_rows(path)

    def test_email_layout_contains_logo_typography_and_responsive_rules(self):
        path = self.write_csv([SAMPLE])
        rows = generate_report.read_rows(path)
        output = generate_report.render(rows, "periodo", "America/Mexico_City")

        self.assertIn("cid:" + LOGO_CID, output)
        self.assertIn("Logotipo oficial de ECOSUR", output)
        self.assertIn("eco-logo-chip", output)
        self.assertIn(FONT_STACK, output)
        self.assertIn("max-width:600px", output)
        self.assertIn("@media screen and (max-width:620px)", output)
        self.assertIn("@media (prefers-color-scheme: dark)", output)
        self.assertNotIn("Visitar ECOSUR", output)
        self.assertIn("Visitar el sitio oficial", output)
        self.assertNotIn("data:image", output)

    def test_html_is_balanced_and_images_have_accessible_attributes(self):
        path = self.write_csv([SAMPLE])
        rows = generate_report.read_rows(path)
        output = generate_report.render(rows, "periodo", "America/Mexico_City")

        checker = HtmlStructureChecker()
        checker.feed(output)
        checker.close()

        self.assertEqual(checker.errors, [])
        self.assertEqual(checker.stack, [])
        self.assertTrue(checker.images)
        self.assertTrue(all(image.get("alt") for image in checker.images))
        self.assertTrue(all(image.get("width") and image.get("height") for image in checker.images))
        self.assertTrue(all(link.get("href", "").startswith("https://") for link in checker.links))

    def test_home_url_is_escaped_in_links(self):
        path = self.write_csv([])
        rows = generate_report.read_rows(path)
        output = generate_report.render(
            rows, "periodo", "America/Mexico_City", "https://example.com/?a=1&b=2"
        )
        self.assertIn('href="https://example.com/?a=1&amp;b=2"', output)

    def test_status_badges_only_color_known_states(self):
        approved = generate_report.render_status("approved")
        rejected = generate_report.render_status("rejected")
        other = generate_report.render_status("pendiente")
        self.assertIn("#067647", approved)
        self.assertIn("#b42318", rejected)
        self.assertIn("#475467", other)
        self.assertNotIn("<script", generate_report.render_status("<script>"))

    def test_cli_writes_html(self):
        path = self.write_csv([SAMPLE])
        output_path = self.base / "report.html"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(generate_report.__file__)),
                "--csv", str(path),
                "--html", str(output_path),
                "--period-label", "periodo",
                "--timezone", "America/Mexico_City",
                "--home-url", "https://example.com/",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("Reunión de prueba 01", content)
        self.assertIn('href="https://example.com/"', content)


if __name__ == "__main__":
    unittest.main()
