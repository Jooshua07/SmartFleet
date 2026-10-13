from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUS_ACCOUNTS_PAGE = PROJECT_ROOT / "app_pages" / "accounts.py"

SUMMARY = {
    "shared_general_costs": Decimal("7535.00"),
    "buses": [
        {
            "bus_id": 1,
            "registration_number": "AIH123",
            "status": "ACTIVE",
            "recorded_revenue": Decimal("12000.00"),
            "confirmed_revenue": Decimal("12000.00"),
            "estimated_revenue": Decimal("0.00"),
            "direct_costs": Decimal("8000.00"),
            "allocated_costs": Decimal("0.00"),
            "attributed_costs": Decimal("8000.00"),
            "recorded_contribution": Decimal("4000.00"),
        },
        {
            "bus_id": 2,
            "registration_number": "AIF123",
            "status": "ACTIVE",
            "recorded_revenue": Decimal("9000.00"),
            "confirmed_revenue": Decimal("9000.00"),
            "estimated_revenue": Decimal("0.00"),
            "direct_costs": Decimal("5000.00"),
            "allocated_costs": Decimal("0.00"),
            "attributed_costs": Decimal("5000.00"),
            "recorded_contribution": Decimal("4000.00"),
        },
    ],
}

DETAIL = {
    "bus": {"id": 1, "registration_number": "AIH123", "status": "ACTIVE"},
    "trend": [
        {
            "month": date(2026, 10, 1),
            "recorded_revenue": Decimal("12000.00"),
            "attributed_costs": Decimal("8000.00"),
            "recorded_contribution": Decimal("4000.00"),
        }
    ],
    "costs_by_category": [{"category_name": "Parts", "amount": Decimal("8000.00")}],
    "recent_transactions": [
        {
            "transaction_date": date(2026, 10, 4),
            "transaction_group": "Attributed cost",
            "title": "AIH tyres",
            "amount": Decimal("4000.00"),
            "detail": "Parts",
        }
    ],
}


class BusAccountsPageTests(unittest.TestCase):
    def test_bus_accounts_page_shows_comparison_and_detail(self):
        with (
            patch("services.bus_account_service.get_bus_contribution_summary", return_value=SUMMARY),
            patch("services.bus_account_service.get_bus_account_detail", return_value=DETAIL),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 13)),
        ):
            app = AppTest.from_file(BUS_ACCOUNTS_PAGE, default_timeout=10).run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Bus Accounts", [subheader.value for subheader in app.subheader])
        self.assertIn("Shared business costs", [metric.label for metric in app.metric])
        self.assertIn("Recorded bus contribution", [metric.label for metric in app.metric])
        self.assertIn("Bus detail", [selectbox.label for selectbox in app.selectbox])
        self.assertIn("**AIH tyres**", [markdown.value for markdown in app.markdown])


if __name__ == "__main__":
    unittest.main()
