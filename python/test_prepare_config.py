#!/usr/bin/env python3
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import prepare_config as pc

ZONE = "America/Mexico_City"
NOW = datetime(2026, 11, 25, 6, 0, tzinfo=ZoneInfo(ZONE))


class PeriodTests(unittest.TestCase):
    def test_rolling_week(self):
        start, end = pc.parse_period({}, ZONE, "rolling_week", now=NOW)
        self.assertEqual(start, NOW - timedelta(days=7))
        self.assertEqual(end, NOW)

    def test_calendar_month(self):
        start, end = pc.parse_period({}, ZONE, "calendar_month", now=NOW)
        self.assertEqual(start, datetime(2026, 11, 1, 0, 0, tzinfo=ZoneInfo(ZONE)))
        self.assertEqual(end, datetime(2026, 12, 1, 0, 0, tzinfo=ZoneInfo(ZONE)))

    def test_previous_calendar_month_at_month_boundary(self):
        boundary = datetime(2026, 12, 1, 0, 0, tzinfo=ZoneInfo(ZONE))
        current_start, _ = pc.parse_period({}, ZONE, "calendar_month", now=boundary)
        previous_start, previous_end = pc.parse_period(
            {}, ZONE, "previous_calendar_month", now=boundary
        )
        self.assertEqual(previous_end, current_start)
        self.assertEqual(previous_start, datetime(2026, 11, 1, 0, 0, tzinfo=ZoneInfo(ZONE)))

    def test_invalid_period_type(self):
        with self.assertRaises(SystemExit):
            pc.parse_period({}, ZONE, "no_existe", now=NOW)


class DatabaseUrlTests(unittest.TestCase):
    def test_production_url_is_allowed(self):
        pc.validate_database_url(
            "postgres://usuario:clave@db.ejemplo.com:5432/eco?sslmode=require",
            {},
        )

    def test_optional_db_and_user_validation(self):
        url = "postgresql://eco_user:clave@db.ejemplo.com:5432/eco?sslmode=require"
        pc.validate_database_url(url, {"REPORT_DB_NAME": "eco", "REPORT_DB_USER": "eco_user"})
        with self.assertRaises(SystemExit):
            pc.validate_database_url(url, {"REPORT_DB_NAME": "otra"})


if __name__ == "__main__":
    unittest.main()
