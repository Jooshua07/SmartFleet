from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORD_EXPENSE_PAGE = PROJECT_ROOT / "app_pages" / "record_expense.py"

CATEGORIES = [
    {"id": 1, "name": "Maintenance"},
    {"id": 2, "name": "Parts"},
    {"id": 3, "name": "Office & Administration"},
]

BUSES = [
    {
        "id": 1,
        "registration_number": "AIH123",
        "driver_name": "Felix",
        "route_name": "Town",
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "registration_number": "AIF123",
        "driver_name": None,
        "route_name": "Market",
        "status": "INACTIVE",
    },
]

RECENT = [
    {
        "id": 10,
        "expense_date": date(2026, 10, 2),
        "category_name": "Parts",
        "amount": Decimal("4000.00"),
        "description": "AIH tyres",
        "vendor_name": "Tyre shop",
        "reference_number": "R001",
        "scope": "BUS",
        "payment_source": "BUSINESS_ACCOUNT",
        "account_name": "Airtel Money",
        "registration_number": "AIH123",
    }
]


class RecordExpensePageTests(unittest.TestCase):
    def _patched_page(self, recent=None):
        patches = [
            patch("services.expense_service.get_operating_expense_categories", return_value=CATEGORIES),
            patch("services.bus_service.get_buses_overview", return_value=BUSES),
            patch("services.expense_service.get_recent_expenses", return_value=recent or []),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 12)),
        ]
        for active_patch in patches:
            active_patch.start()
        self.addCleanup(lambda: [active_patch.stop() for active_patch in reversed(patches)])
        return AppTest.from_file(RECORD_EXPENSE_PAGE, default_timeout=10)

    def test_record_expense_hides_paid_from_and_uses_scope_selector(self):
        app = self._patched_page()
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertNotIn("Paid from", [selectbox.label for selectbox in app.selectbox])
        self.assertIn("Expense scope", [control.label for control in app.segmented_control])
        self.assertIn("Expense title", [field.label for field in app.text_input])

    def test_specific_bus_scope_shows_active_and_deactivated_buses(self):
        app = self._patched_page()
        app.run()
        app.segmented_control[0].set_value("Specific Bus").run()

        self.assertEqual(len(app.exception), 0)
        bus_select = next(selectbox for selectbox in app.selectbox if selectbox.label == "Bus")
        self.assertIn("AIH123 | Felix", bus_select.options)
        self.assertIn("AIF123 | No driver", bus_select.options)

    def test_recent_expense_uses_expense_title_as_card_title(self):
        app = self._patched_page(recent=RECENT)
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("**AIH tyres**", [markdown.value for markdown in app.markdown])
        self.assertNotIn("Paid from", [selectbox.label for selectbox in app.selectbox])


if __name__ == "__main__":
    unittest.main()
