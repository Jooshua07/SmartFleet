import unittest
from pathlib import Path
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


class RecordCashingPageTests(unittest.TestCase):
    def _patched_page(self):
        patches = [
            patch("services.bus_service.get_buses_overview", return_value=BUSES),
            patch(
                "services.cashing_service.get_collection_destination_account",
                return_value=COLLECTION_ACCOUNT,
            ),
            patch("services.cashing_service.get_recent_cashing_collections", return_value=[]),
        ]
        for active_patch in patches:
            active_patch.start()
        self.addCleanup(lambda: [active_patch.stop() for active_patch in reversed(patches)])
        return AppTest.from_file(RECORD_CASHING_PAGE, default_timeout=10)

    def test_page_starts_with_one_bus_picker(self):
        app = self._patched_page()
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.multiselect), 1)
        self.assertEqual(app.multiselect[0].label, "Bus(es)")
        self.assertEqual(len(app.number_input), 0)
        self.assertEqual(len(app.info), 1)

    def test_one_bus_selection_shows_one_amount_field(self):
        app = self._patched_page()
        app.run()
        app.multiselect[0].set_value(["ABC123 | Mary Banda"]).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual([field.label for field in app.number_input], ["Amount (K)"])
        self.assertEqual([toggle.label for toggle in app.toggle], ["Add Sunday"])

    def test_multiple_buses_default_to_one_common_amount(self):
        app = self._patched_page()
        app.run()
        app.multiselect[0].set_value(["ABC123 | Mary Banda", "BCD223 | John Phiri"]).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual([field.label for field in app.number_input], ["Amount per selected bus (K)"])
        self.assertEqual(
            [toggle.label for toggle in app.toggle],
            ["Add Sunday", "Different amounts per bus"],
        )

    def test_multiple_buses_can_switch_to_per_bus_amounts(self):
        app = self._patched_page()
        app.run()
        app.multiselect[0].set_value(["ABC123 | Mary Banda", "BCD223 | John Phiri"]).run()
        app.toggle[1].set_value(True).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            [field.label for field in app.number_input],
            ["Amount (K)", "Amount (K)"],
        )


if __name__ == "__main__":
    unittest.main()
