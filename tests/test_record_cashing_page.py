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

SMART_COLLECTION = {
    "id": 10,
    "collection_date": date(2026, 10, 4),
    "financial_account_id": 9,
    "financial_transaction_id": 50,
    "total_amount": Decimal("3000.00"),
    "expected_total": Decimal("3600.00"),
    "unallocated_amount": Decimal("-600.00"),
    "coverage_start": date(2026, 10, 1),
    "coverage_end": date(2026, 10, 3),
    "cashing_mode": "STANDARD",
    "difference_classification": "UNKNOWN_DIFFERENCE",
    "notes": "Initial notes",
    "account_name": "Airtel Money",
}

SMART_DETAILS = {
    "collection": SMART_COLLECTION,
    "entries": [
        {
            "id": 101,
            "bus_id": 1,
            "registration_number": "ABC123",
            "normal_days": 3,
            "normal_daily_rate": Decimal("600.00"),
            "sunday_days": 0,
            "sunday_rate": Decimal("300.00"),
            "actual_amount": Decimal("1800.00"),
            "expected_amount": Decimal("1800.00"),
            "variance": Decimal("0.00"),
            "allocation_provenance": "ESTIMATED_STANDARD",
            "difference_classification": "MATCHED",
            "worked_days_adjusted": False,
            "sunday_worked": False,
            "explanation": None,
            "notes": None,
        },
        {
            "id": 102,
            "bus_id": 2,
            "registration_number": "BCD223",
            "normal_days": 3,
            "normal_daily_rate": Decimal("600.00"),
            "sunday_days": 0,
            "sunday_rate": Decimal("300.00"),
            "actual_amount": Decimal("1800.00"),
            "expected_amount": Decimal("1800.00"),
            "variance": Decimal("0.00"),
            "allocation_provenance": "ESTIMATED_STANDARD",
            "difference_classification": "MATCHED",
            "worked_days_adjusted": False,
            "sunday_worked": False,
            "explanation": None,
            "notes": None,
        },
    ],
}

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
    def _patched_page(self, recent=None, obligations=None, details=None, collection_obligations=None, payments=None):
        patches = [
            patch(
                "services.cashing_service.get_collection_destination_account",
                return_value=COLLECTION_ACCOUNT,
            ),
            patch("services.smart_cashing_service.get_smart_cashing_preview", return_value=PREVIEW),
            patch("services.cashing_service.get_recent_cashing_collections", return_value=recent or []),
            patch("services.cashing_service.get_cashing_collection", return_value=details or SMART_DETAILS),
            patch(
                "services.smart_cashing_service.list_open_cashing_obligations",
                return_value=obligations or [],
            ),
            patch(
                "services.smart_cashing_service.get_cashing_obligations_for_collection",
                return_value=collection_obligations or [],
            ),
            patch(
                "services.smart_cashing_service.list_cashing_obligation_payments",
                return_value=payments or [],
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
        self.assertIn("Correct", [button.label for button in app.button])

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

    def test_human_opens_smart_correction_from_recent_record(self):
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
        correct_button = next(button for button in app.button if button.label == "Correct")
        correct_button.click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Correct smart cashing", [subheader.value for subheader in app.subheader])
        labels = [field.label for field in app.number_input]
        self.assertIn("Actual received (K)", labels)
        self.assertIn("Bus allocation (K)", labels)
        self.assertIn("Correction note", [field.label for field in app.text_area])

    def test_smart_record_with_obligation_locks_correction_and_delete(self):
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
                "difference_classification": "CONFIRMED_UNPAID_OBLIGATION",
                "financial_account_id": 9,
                "notes": None,
                "account_name": "Airtel Money",
                "bus_count": 2,
                "obligation_count": 1,
                "outstanding_amount": Decimal("600.00"),
            }
        ]
        app = self._patched_page(recent=recent)
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn(
            "Correction locked by obligations or payments.",
            [caption.value for caption in app.caption],
        )

    def test_details_show_payment_history_for_obligation(self):
        obligation = {
            "id": 5,
            "collection_id": 10,
            "remittance_id": 20,
            "amount": Decimal("600.00"),
            "outstanding_amount": Decimal("300.00"),
            "responsible_party_type": "ASSIGNED_DRIVER",
            "responsible_party_name": "Mary Banda",
            "recognized_date": date(2026, 10, 4),
            "status": "PARTIALLY_SETTLED",
            "notes": "Short cashing",
            "registration_number": "ABC123",
            "expected_amount": Decimal("1800.00"),
            "actual_amount": Decimal("1200.00"),
            "paid_amount": Decimal("300.00"),
        }
        payment = {
            "id": 7,
            "payment_date": date(2026, 10, 8),
            "amount": Decimal("300.00"),
            "notes": "Part payment",
            "account_name": "Airtel Money",
        }
        app = self._patched_page(collection_obligations=[obligation], payments=[payment])
        app.session_state["detail_cashing_id"] = 10
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Payment history", [caption.value for caption in app.caption])
        self.assertTrue(any("08 Oct 2026" in caption.value for caption in app.caption))


if __name__ == "__main__":
    unittest.main()
