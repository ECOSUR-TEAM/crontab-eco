#!/usr/bin/env python3
import argparse
import csv
import html
import sys
from pathlib import Path

EXPECTED_COLUMNS = ["id", "inicio_local", "fin_local", "motivo", "estado"]
TH_STYLE = "padding:8px;border:1px solid #d0d5dd;background:#f2f4f7;text-align:left;font-size:13px;"
TD_STYLE = "padding:8px;border:1px solid #d0d5dd;font-size:13px;"
TABLE_STYLE = "border-collapse:collapse;width:100%;max-width:720px;"
BODY_STYLE = "margin:0;padding:24px;background:#ffffff;color:#101828;font-family:Arial,Helvetica,sans-serif;"
BOX_STYLE = "max-width:720px;margin:0 auto;"


def escape(value: str) -> str:
    return html.escape(value if value is not None else "", quote=True)


def read_rows(csv_path: Path) -> list:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(
                "Columnas inesperadas en el CSV. Se esperaban: "
                + ", ".join(EXPECTED_COLUMNS)
            )
        rows = []
        for row in reader:
            if None in row or any(row.get(column) is None for column in EXPECTED_COLUMNS):
                raise ValueError("Una fila del CSV no tiene las columnas esperadas.")
            rows.append(row)
    return rows


def render(rows: list, period_label: str, timezone_name: str) -> str:
    safe_period = escape(period_label)
    safe_timezone = escape(timezone_name)
    count = len(rows)

    if rows:
        body = "".join(
            "<tr>"
            + "".join(
                "<td style=\"{style}\">{value}</td>".format(
                    style=TD_STYLE, value=escape(row[column])
                )
                for column in EXPECTED_COLUMNS
            )
            + "</tr>"
            for row in rows
        )
        headers = "".join(
            "<th style=\"{style}\">{label}</th>".format(
                style=TH_STYLE,
                label=escape(
                    {
                        "id": "ID",
                        "inicio_local": "Inicio",
                        "fin_local": "Fin",
                        "motivo": "Motivo",
                        "estado": "Estado",
                    }[column]
                ),
            )
            for column in EXPECTED_COLUMNS
        )
        table = (
            "<table style=\"{style}\"><thead><tr>{headers}</tr></thead>"
            "<tbody>{body}</tbody></table>"
        ).format(style=TABLE_STYLE, headers=headers, body=body)
        summary = "Se registraron {count} reservas en el periodo.".format(count=count)
    else:
        table = ""
        summary = "No hay reservas en el periodo solicitado."

    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        "<title>Eco - Reporte semanal de reservas</title></head>"
        "<body style=\"{body_style}\"><div style=\"{box_style}\">"
        "<h1 style=\"font-size:20px;margin:0 0 16px;\">Eco - Reporte semanal de reservas</h1>"
        "<p style=\"font-size:14px;margin:0 0 8px;\">Periodo: {period} ({tz})</p>"
        "<p style=\"font-size:14px;margin:0 0 16px;\">{summary}</p>"
        "{table}</div></body></html>"
    ).format(
        body_style=BODY_STYLE,
        box_style=BOX_STYLE,
        period=safe_period,
        tz=safe_timezone,
        summary=summary,
        table=table,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--period-label", default="")
    parser.add_argument("--timezone", default="America/Mexico_City")
    args = parser.parse_args()

    try:
        rows = read_rows(Path(args.csv))
    except (OSError, ValueError, csv.Error) as exc:
        print("Error al leer el CSV: {}".format(exc), file=sys.stderr)
        return 1

    output = Path(args.html)
    output.write_text(
        render(rows, args.period_label, args.timezone), encoding="utf-8"
    )
    print("HTML generado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
