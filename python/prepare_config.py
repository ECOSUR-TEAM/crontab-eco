#!/usr/bin/env python3
import argparse
import shlex
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlsplit

from load_env import parse_env

PERIOD_TYPES = (
    "rolling_week",
    "calendar_month",
    "previous_calendar_month",
)
EXPORT_KEYS = (
    "DATABASE_URL",
    "RESEND_API_KEY",
    "REPORT_FROM",
    "REPORT_TO",
    "REPORT_TIMEZONE",
    "REPORT_MODE",
    "REPORT_PERIOD_TYPE",
    "REPORT_DEDUPE",
    "REPORT_PERIOD_START",
    "REPORT_PERIOD_END",
    "REPORT_PERIOD_LABEL",
)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def validate_database_url(url: str, values: dict) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("postgres", "postgresql"):
        fail("DATABASE_URL debe usar el esquema postgres o postgresql.")
    if not parts.hostname:
        fail("DATABASE_URL no incluye servidor.")
    expected_db = values.get("REPORT_DB_NAME")
    if expected_db and unquote(parts.path) != "/" + expected_db:
        fail("DATABASE_URL no apunta a la base esperada en REPORT_DB_NAME.")
    expected_user = values.get("REPORT_DB_USER")
    if expected_user and unquote(parts.username or "") != expected_user:
        fail("DATABASE_URL no usa el usuario esperado en REPORT_DB_USER.")


def get_zone(timezone_name: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(timezone_name)
    except Exception:
        fail("REPORT_TIMEZONE no es una zona horaria válida.")


def parse_period(values: dict, timezone_name: str, period_type: str, now=None) -> tuple:
    zone = get_zone(timezone_name)
    if now is None:
        now = datetime.now(zone)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=zone)
    else:
        now = now.astimezone(zone)
    now = now.replace(second=0, microsecond=0)

    if period_type == "rolling_week":
        return now - timedelta(days=7), now

    if period_type in ("calendar_month", "previous_calendar_month"):
        anchor = now
        if period_type == "previous_calendar_month":
            anchor = now - timedelta(days=1)
        start = anchor.replace(day=1, hour=0, minute=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    fail("REPORT_PERIOD_TYPE no válido: " + period_type)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True)
    parser.add_argument("--period-type", default=None)
    args = parser.parse_args()

    values = parse_env(Path(args.env))
    required = ("DATABASE_URL", "RESEND_API_KEY", "REPORT_FROM", "REPORT_TO")
    missing = [key for key in required if not values.get(key)]
    if missing:
        fail("Faltan variables obligatorias: " + ", ".join(missing))

    validate_database_url(values["DATABASE_URL"], values)

    timezone_name = values.get("REPORT_TIMEZONE") or "America/Mexico_City"
    period_type = args.period_type or values.get("REPORT_PERIOD_TYPE") or "rolling_week"
    if period_type not in PERIOD_TYPES:
        fail("REPORT_PERIOD_TYPE no válido: " + period_type)

    start, end = parse_period(values, timezone_name, period_type)

    dedupe = values.get("REPORT_DEDUPE")
    if dedupe is None:
        dedupe = "1"
    if dedupe not in ("0", "1"):
        fail("REPORT_DEDUPE debe ser 0 o 1.")

    values["REPORT_TIMEZONE"] = timezone_name
    values["REPORT_MODE"] = "production"
    values["REPORT_PERIOD_TYPE"] = period_type
    values["REPORT_DEDUPE"] = dedupe
    values["REPORT_PERIOD_START"] = start.isoformat()
    values["REPORT_PERIOD_END"] = end.isoformat()
    values["REPORT_PERIOD_LABEL"] = "{} a {}".format(
        start.strftime("%Y-%m-%d %H:%M %Z"), end.strftime("%Y-%m-%d %H:%M %Z")
    )

    for key in EXPORT_KEYS:
        print("export {}={}".format(key, shlex.quote(values[key])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
