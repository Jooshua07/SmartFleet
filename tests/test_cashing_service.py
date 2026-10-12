from datetime import date, datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from services.cashing_service import (
    _clean_direct_entry,
    _clean_direct_entries,
    _coerce_collection_date,
    _format_duplicate,
    get_collection_destination_account,
)


class CashingServiceTests(unittest.TestCase):
    def test_clean_direct_entry_combines_normal_and_sunday_amounts(self):
        entry = _clean_direct_entry(
            {
                "bus_id": 7,
                "normal_amount": "600",
                "sunday_amount": "300",
                "explanation": " Sunday ",
                "notes": " Paid late ",
            }
        )

        self.assertEqual(entry["bus_id"], 7)
        self.assertEqual(entry["normal_days"], 1)
        self.assertEqual(entry["sunday_days"], 1)
        self.assertEqual(entry["actual_amount"], Decimal("900"))
        self.assertEqual(entry["explanation"], "Sunday")
        self.assertEqual(entry["notes"], "Paid late")

    def test_clean_direct_entry_rejects_zero_total(self):
        with self.assertRaisesRegex(ValueError, "Enter an amount"):
            _clean_direct_entry({"bus_id": 7, "normal_amount": 0, "sunday_amount": 0})

    def test_clean_direct_entry_rejects_negative_sunday_amount(self):
        with self.assertRaisesRegex(ValueError, "Sunday amount cannot be negative"):
            _clean_direct_entry({"bus_id": 7, "normal_amount": 600, "sunday_amount": -1})

    def test_clean_direct_entries_keeps_selected_rows_only(self):
        entries = _clean_direct_entries(
            [
                {"include": False, "bus_id": 1, "normal_amount": 600},
                {"include": True, "bus_id": 2, "normal_amount": 700},
            ]
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["bus_id"], 2)

    def test_clean_direct_entries_requires_at_least_one_selected_bus(self):
        with self.assertRaisesRegex(ValueError, "Choose at least one bus"):
            _clean_direct_entries([{"include": False, "bus_id": 1, "normal_amount": 600}])

    def test_coerce_collection_date_accepts_date_and_datetime(self):
        self.assertEqual(_coerce_collection_date(date(2026, 10, 12)), date(2026, 10, 12))
        self.assertEqual(
            _coerce_collection_date(datetime(2026, 10, 12, 10, 30)),
            date(2026, 10, 12),
        )

    def test_format_duplicate_lists_first_matches(self):
        message = _format_duplicate(
            [
                {"registration_number": "ABC123", "collection_date": date(2026, 10, 12)},
                {"registration_number": "BCD223", "collection_date": date(2026, 10, 12)},
                {"registration_number": "CDE333", "collection_date": date(2026, 10, 12)},
                {"registration_number": "DEF444", "collection_date": date(2026, 10, 12)},
            ]
        )

        self.assertIn("ABC123 on 12/10/2026", message)
        self.assertIn("and 1 more", message)

    def test_collection_destination_uses_airtel_money_account(self):
        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, sql, params=None):
                self.params = params

            def fetchone(self):
                return {"id": 2, "name": "Airtel Money", "account_type": "AIRTEL_MONEY"}

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, row_factory=None):
                return Cursor()

        with (
            patch("services.cashing_service.get_default_collection_account_type", return_value="AIRTEL_MONEY"),
            patch("services.cashing_service.get_connection", return_value=Connection()),
        ):
            account = get_collection_destination_account()

        self.assertEqual(account["account_type"], "AIRTEL_MONEY")


if __name__ == "__main__":
    unittest.main()
