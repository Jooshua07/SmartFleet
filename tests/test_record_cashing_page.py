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
    def _patched_page(self, recent=None, obligations=None):
        patches = [
            patch(
                "services.cashing_service.get_collection_destination_account",
                return_value=COLLECTION_ACCOUNT,
            ),
            patch("services.smart_cashing_service.get_smart_cashing_preview", return_value=PREVIEW),
            patch("services.cashing_service.get_recent_cashing_collections", return_value=recent or []),
            patch(
                "services.smart_cashing_service.list_open_cashing_obligations",
                return_value=obligations or [],
            ),
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

    def test_recent_smart_collection_shows_received_expected_difference(self):
        recent = [
            {
                "id": 10,
                "collection_date": date(2026, 10, 4),
                "total_amount": Decimal("3000.00"),
                "expected_total": Decimal("3600.00"),
                "unallocated_amount": Decimal("-600.00"),
                "coverage_start": date(2026, 10, 1),
                "coverage_end": date(2026, 10, 3),
                "cashing_mode": "STANDARD",
                "difference_classification": "UNKNOWN_DIFFERENCE",
                "financial_account_id": 9,
                "notes": None,
                "account_name": "Airtel Money",
                "bus_count": 2,
                "obligation_count": 0,
                "outstanding_amount": Decimal("0.00"),
            }
        ]
        app = self._patched_page(recent=recent)
        app.run()

        self.assertEqual(len(app.exception), 0)
        labels = [metric.label for metric in app.metric]
        self.assertIn("Received", labels)
        self.assertIn("Expected", labels)
        self.assertIn("Difference", labels)
        self.assertIn("Details", [button.label for button in app.button])

    def test_open_obligations_section_renders_payment_action(self):
        obligations = [
            {
                "id": 5,
                "collection_id": 10,
                "remittance_id": 20,
                "amount": Decimal("600.00"),
                "outstanding_amount": Decimal("600.00"),
                "responsible_party_type": "ASSIGNED_DRIVER",
                "responsible_party_name": "Mary Banda",
                "recognized_date": date(2026, 10, 4),
                "status": "OPEN",
                "notes": "Short cashing",
                "collection_date": date(2026, 10, 4),
                "registration_number": "ABC123",
                "expected_amount": Decimal("1800.00"),
                "actual_amount": Decimal("1200.00"),
                "paid_amount": Decimal("0.00"),
            }
        ]
        app = self._patched_page(obligations=obligations)
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Open cashing obligations", [subheader.value for subheader in app.subheader])
        self.assertIn("Record payment", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
