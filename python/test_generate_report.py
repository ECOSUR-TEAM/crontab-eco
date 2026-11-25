#!/usr/bin/env python3
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import generate_report

HEADER = generate_report.EXPECTED_COLUMNS
SAMPLE = {
    "id": "1",
    "inicio_local": "2026-11-23 09:00",
    "fin_local": "2026-11-23 09:20",
    "motivo": "Reunión de prueba 01",
    "estado": "approved",
}


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
        self.assertEqual(len(rows), 1)
        output = generate_report.render(rows, "2026-11-23 a 2026-11-30", "America/Mexico_City")
        self.assertIn("Se registraron 1 reservas", output)
        self.assertIn("Reunión de prueba 01", output)
        self.assertIn("approved", output)
        self.assertIn("2026-11-23 09:00", output)
        self.assertIn("<table", output)
        self.assertNotIn("<script", output)

    def test_empty_csv(self):
        path = self.write_csv([])
        rows = generate_report.read_rows(path)
        output = generate_report.render(rows, "periodo", "America/Mexico_City")
        self.assertIn("No hay reservas en el periodo solicitado.", output)
        self.assertNotIn("<table", output)

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
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Reunión de prueba 01", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
