import unittest
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORD_CASHING_PAGE = PROJECT_ROOT / "app_pages" / "record_cashing.py"

BUSES = [
    {
        "id": 1,
        "registration_number": "ABC123",
        "driver_name": "Mary Banda",
        "route_name": "Town",
    },
    {
        "id": 2,
        "registration_number": "BCD223",
        "driver_name": "John Phiri",
        "route_name": "Market",
    },
]

COLLECTION_ACCOUNT = {"id": 9, "name": "Airtel Money", "account_type": "AIRTEL_MONEY"}

PREVIEW = {
    "collection_type": "SUNDAY",
    "coverage_start": date(2026, 10, 1),
    "coverage_end": date(2026, 10, 3),
    "previous_sunday": None,
    "rates": {"NORMAL_DAY": Decimal("600.00"), "SUNDAY": Decimal("300.00")},
    "expected_total": Decimal("3600.00"),
    "buses": [
        {
            **BUSES[0],
            "normal_days": 3,
            "sunday_days": 0,
            "normal_daily_rate": Decimal("600.00"),
            "sunday_rate": Decimal("300.00"),
            "expected_amount": Decimal("1800.00"),
        },
        {
            **BUSES[1],
            "normal_days": 3,
            "sunday_days": 0,
            "normal_daily_rate": Decimal("600.00"),
            "sunday_rate": Decimal("300.00"),
            "expected_amount": Decimal("1800.00"),
        },
    ],
}


class RecordCashingPageTests(unittest.TestCase):
    def _patched_page(self):
        patches = [
            patch(
                "services.cashing_service.get_collection_destination_account",
                return_value=COLLECTION_ACCOUNT,
            ),
            patch("services.smart_cashing_service.get_smart_cashing_preview", return_value=PREVIEW),
            patch("services.cashing_service.get_recent_cashing_collections", return_value=[]),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 4)),
        ]
        for active_patch in patches:
            active_patch.start()
        self.addCleanup(lambda: [active_patch.stop() for active_patch in reversed(patches)])
        return AppTest.from_file(RECORD_CASHING_PAGE, default_timeout=10)

    def test_page_starts_with_smart_cashing_controls(self):
        app = self._patched_page()
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.multiselect), 1)
        self.assertEqual(app.multiselect[0].label, "Bus(es)")
        self.assertIn("Expected cashing", [metric.label for metric in app.metric])
        self.assertEqual([toggle.label for toggle in app.toggle], ["Backfill / edit date"])

    def test_standard_mode_shows_single_actual_received_field(self):
        app = self._patched_page()
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual([field.label for field in app.number_input], ["Actual received (K)"])

    def test_backfill_mode_reveals_date_input(self):
        app = self._patched_page()
        app.run()
        app.toggle[0].set_value(True).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.date_input[0].label, "Collection date")

    def test_adjust_mode_shows_per_bus_fields(self):
        app = self._patched_page()
        app.run()
        app.segmented_control[0].set_value("Adjust Buses").run()

        self.assertEqual(len(app.exception), 0)
        labels = [field.label for field in app.number_input]
        self.assertIn("Normal days worked", labels)
        self.assertIn("Bus allocation (K)", labels)


if __name__ == "__main__":
    unittest.main()
