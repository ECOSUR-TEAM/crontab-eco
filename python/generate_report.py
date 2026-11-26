#!/usr/bin/env python3
import argparse
import csv
import html
import sys
from pathlib import Path

from email_brand import FONT_STACK, HOME_URL_DEFAULT, LOGO_CID

EXPECTED_COLUMNS = ["id", "inicio_local", "fin_local", "motivo", "estado"]
LABELS = {
    "id": "ID",
    "inicio_local": "Inicio",
    "fin_local": "Fin",
    "motivo": "Motivo",
    "estado": "Estado",
}

FONT_STYLE = "font-family:{};".format(FONT_STACK)
TH_STYLE = (
    "padding:10px 8px;border:1px solid #d0d5dd;background:#f2f4f7;"
    "text-align:left;font-size:12px;line-height:1.4;color:#344054;"
    "text-transform:uppercase;letter-spacing:.04em;"
)
TD_STYLE = (
    "padding:10px 8px;border:1px solid #d0d5dd;font-size:13px;"
    "line-height:1.5;color:#101828;vertical-align:top;"
)
TABLE_STYLE = "border-collapse:collapse;width:100%;font-size:13px;"
INFO_CELL_STYLE = (
    "width:50%;padding:12px 14px;background:#f6f9f7;"
    "border:1px solid #e1ebe6;border-radius:8px;"
)

# Reglas que no se pueden poner en línea: responsive y modo oscuro.
EMAIL_CSS = """
  body, table, td, a {-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}
  table, td {mso-table-lspace:0pt;mso-table-rspace:0pt;}
  img {-ms-interpolation-mode:bicubic;border:0;line-height:100%;outline:none;text-decoration:none;}
  a {text-decoration:none;}
  @media screen and (max-width:620px) {
    .eco-wrapper {padding:12px 8px !important;}
    .eco-pad {padding-left:20px !important;padding-right:20px !important;}
    .eco-brand {text-align:left !important;padding-top:16px !important;}
    .eco-stack {display:block !important;width:100% !important;box-sizing:border-box !important;}
    .eco-stack + .eco-stack {padding-top:10px !important;}
    .eco-button-cell {padding:0 !important;}
    .eco-button {display:block !important;width:100% !important;box-sizing:border-box !important;text-align:center !important;}
    .eco-data th, .eco-data td {padding:8px 5px !important;font-size:12px !important;word-break:break-word;}
  }
  @media (prefers-color-scheme: dark) {
    .eco-outer {background-color:#0d1b16 !important;}
    .eco-card {background-color:#13251e !important;border-color:#264336 !important;}
    .eco-header, .eco-footer {background-color:#0f2019 !important;border-color:#264336 !important;}
    .eco-logo-chip {background-color:#ffffff !important;}
    .eco-info {background-color:#1b342a !important;border-color:#2d4e40 !important;}
    .eco-title, .eco-text {color:#e7f3ed !important;}
    .eco-muted {color:#a8c6ba !important;}
    .eco-data th {background-color:#1b342a !important;color:#d9ece4 !important;border-color:#2d4e40 !important;}
    .eco-data td {color:#e7f3ed !important;border-color:#2d4e40 !important;}
    .eco-empty {background-color:#172e25 !important;color:#cfe4da !important;border-color:#2d4e40 !important;}
  }
"""


def escape(value: str, quote: bool = True) -> str:
    return html.escape(value if value is not None else "", quote=quote)


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


def render_status(value: str) -> str:
    status = escape(value)
    normalized = (value or "").strip().lower()
    if normalized == "approved":
        color, background = "#067647", "#e7f6ef"
    elif normalized == "rejected":
        color, background = "#b42318", "#fdecee"
    else:
        color, background = "#475467", "#f2f4f7"
    return (
        '<span style="display:inline-block;padding:3px 8px;border-radius:12px;'
        'background:{background};color:{color};font-size:12px;line-height:1.4;'
        'font-weight:600;">{status}</span>'
    ).format(background=background, color=color, status=status)


def render_table(rows: list) -> str:
    headers = "".join(
        '<th style="{style}">{label}</th>'.format(style=TH_STYLE, label=escape(LABELS[column]))
        for column in EXPECTED_COLUMNS
    )
    body = "".join(
        "<tr>"
        + "".join(
            '<td style="{style}">{value}</td>'.format(
                style=TD_STYLE,
                value=render_status(row[column]) if column == "estado" else escape(row[column]),
            )
            for column in EXPECTED_COLUMNS
        )
        + "</tr>"
        for row in rows
    )
    return (
        '<table role="presentation" class="eco-data" width="100%" cellpadding="0" '
        'cellspacing="0" border="0" style="{style}">'
        "<thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>"
    ).format(style=TABLE_STYLE, headers=headers, body=body)


def render_empty() -> str:
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr><td class="eco-empty" style="padding:20px;border:1px dashed '
        '#b7d2c5;border-radius:8px;background:#f6f9f7;color:#475467;text-align:center;'
        'font-size:14px;line-height:1.6;">'
        "No hay reservas en el periodo solicitado."
        "</td></tr></table>"
    )


def render(rows: list, period_label: str, timezone_name: str, home_url: str = HOME_URL_DEFAULT) -> str:
    count = len(rows)
    safe_period = escape(period_label)
    safe_timezone = escape(timezone_name)
    safe_home_url = escape(home_url or HOME_URL_DEFAULT, quote=True)

    if count == 1:
        summary = "Se registró 1 reserva en el periodo."
    elif count:
        summary = "Se registraron {count} reservas en el periodo.".format(count=count)
    else:
        summary = "No hay reservas en el periodo solicitado."

    detail = render_table(rows) if rows else render_empty()
    preheader = "{} {}".format(summary, safe_period)

    return (
        "<!doctype html>"
        '<html lang="es" xmlns="http://www.w3.org/1999/xhtml"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="supported-color-schemes" content="light dark">'
        "<title>ECOSUR - Reporte de reservas</title>"
        '<style type="text/css">{css}</style>'
        "</head>"
        '<body class="eco-outer" style="margin:0;padding:0;background-color:#f2f6f4;'
        '{font_style}color:#101828;">'
        '<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;'
        'opacity:0;overflow:hidden;mso-hide:all;">{preheader}</div>'
        '<table role="presentation" class="eco-outer" width="100%" cellpadding="0" '
        'cellspacing="0" border="0" bgcolor="#f2f6f4" style="width:100%;'
        'background-color:#f2f6f4;">'
        '<tr><td align="center" class="eco-wrapper" style="padding:32px 12px;">'
        '<table role="presentation" class="eco-card" width="600" cellpadding="0" '
        'cellspacing="0" border="0" bgcolor="#ffffff" style="width:100%;max-width:600px;'
        'background-color:#ffffff;border:1px solid #dfe9e4;border-radius:14px;'
        'overflow:hidden;">'
        '<tr><td class="eco-header eco-pad" bgcolor="#ffffff" style="padding:24px 32px;'
        'background-color:#ffffff;border-bottom:1px solid #e3ebe7;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        "<tr>"
        '<td style="vertical-align:middle;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="background-color:#ffffff;border-radius:12px;">'
        '<tr><td class="eco-logo-chip" bgcolor="#ffffff" style="padding:8px;'
        'background-color:#ffffff;border-radius:12px;">'
        '<a href="{home_url}" style="display:inline-block;">'
        '<img src="cid:{logo_cid}" width="56" height="56" alt="Logotipo oficial de ECOSUR" '
        'style="display:block;width:56px;height:56px;border:0;outline:none;'
        'text-decoration:none;">'
        "</a></td></tr></table></td>"
        '<td align="right" class="eco-brand" style="vertical-align:middle;text-align:right;">'
        '<div class="eco-title" style="font-size:16px;line-height:1.3;font-weight:700;'
        'color:#0b3d2e;">ECOSUR</div>'
        '<div class="eco-muted" style="font-size:12px;line-height:1.4;color:#5b6f66;'
        'margin-top:2px;">Reportes de reservas</div>'
        "</td></tr></table></td></tr>"
        '<tr><td class="eco-pad" style="padding:32px;">'
        '<p class="eco-muted" style="margin:0 0 8px;font-size:11px;line-height:1.4;'
        'font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#527568;">'
        "Reporte de reservas</p>"
        '<h1 class="eco-title" style="margin:0 0 12px;font-size:24px;line-height:1.3;'
        'font-weight:700;color:#10261f;">Resumen del periodo</h1>'
        '<p class="eco-text" style="margin:0 0 24px;font-size:14px;line-height:1.6;'
        'color:#344054;">{summary}</p>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr>'
        '<td class="eco-stack eco-info" style="{info_style}">'
        '<div class="eco-muted" style="font-size:11px;line-height:1.4;font-weight:600;'
        'text-transform:uppercase;letter-spacing:.06em;color:#527568;">Periodo</div>'
        '<div class="eco-text" style="margin-top:4px;font-size:13px;line-height:1.5;'
        'color:#10261f;">{period}</div>'
        '<div class="eco-muted" style="margin-top:2px;font-size:11px;line-height:1.4;'
        'color:#66785f;">{timezone}</div>'
        "</td>"
        '<td class="eco-stack eco-info" style="{info_style}">'
        '<div class="eco-muted" style="font-size:11px;line-height:1.4;font-weight:600;'
        'text-transform:uppercase;letter-spacing:.06em;color:#527568;">Reservas</div>'
        '<div class="eco-text" style="margin-top:4px;font-size:22px;line-height:1.2;'
        'font-weight:700;color:#0b3d2e;">{count}</div>'
        "</td></tr></table>"
        '<div style="height:24px;line-height:24px;font-size:1px;">&nbsp;</div>'
        '{detail}'
        '<div style="height:28px;line-height:28px;font-size:1px;">&nbsp;</div>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr><td align="center" class="eco-button-cell" '
        'style="padding:0;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:0 auto;">'
        '<tr><td bgcolor="#279669" style="background-color:#279669;'
        'border-radius:8px;">'
        '<a class="eco-button" href="{home_url}" style="display:inline-block;'
        'padding:12px 24px;color:#ffffff;font-size:14px;line-height:1.3;'
        'font-weight:700;text-align:center;">Visitar ECOSUR</a>'
        "</td></tr></table></td></tr></table>"
        "</td></tr>"
        '<tr><td class="eco-footer eco-pad" bgcolor="#ffffff" style="padding:20px 32px;'
        'background-color:#ffffff;border-top:1px solid #e3ebe7;">'
        '<p class="eco-muted" style="margin:0;font-size:12px;line-height:1.6;'
        'color:#66785f;">'
        "Correo generado automáticamente con el reporte de reservas de ECOSUR. "
        '<a href="{home_url}" style="color:#0b3d2e;text-decoration:underline;">'
        "Visitar el sitio oficial</a>."
        "</p></td></tr>"
        "</table></td></tr></table></body></html>"
    ).format(
        css=EMAIL_CSS,
        font_style=FONT_STYLE,
        preheader=preheader,
        home_url=safe_home_url,
        logo_cid=LOGO_CID,
        summary=escape(summary),
        period=safe_period,
        timezone=safe_timezone,
        info_style=INFO_CELL_STYLE + FONT_STYLE,
        count=count,
        detail=detail,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--period-label", default="")
    parser.add_argument("--timezone", default="America/Mexico_City")
    parser.add_argument("--home-url", default=HOME_URL_DEFAULT)
    args = parser.parse_args()

    try:
        rows = read_rows(Path(args.csv))
    except (OSError, ValueError, csv.Error) as exc:
        print("Error al leer el CSV: {}".format(exc), file=sys.stderr)
        return 1

    output = Path(args.html)
    output.write_text(
        render(rows, args.period_label, args.timezone, args.home_url), encoding="utf-8"
    )
    print("HTML generado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
