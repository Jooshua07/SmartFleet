from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOME_PAGE = PROJECT_ROOT / "app_pages" / "home.py"


BALANCE = {
    "baseline_date": date(2026, 10, 1),
    "money_in": Decimal("16200.00"),
    "money_out": Decimal("17000.00"),
    "business_balance": Decimal("-800.00"),
    "collections": Decimal("16200.00"),
    "operating_payments": Decimal("2000.00"),
    "financing_in": Decimal("0.00"),
    "financing_out": Decimal("15000.00"),
}


class HomePageTests(unittest.TestCase):
    def test_home_summary_cards_show_general_business_balance(self):
        with (
            patch("services.finance_service.get_business_balance", return_value=BALANCE),
            patch("services.dashboard_service.get_activity_date_bounds", return_value={"earliest_date": None}),
            patch("services.dashboard_service.get_bus_status_counts", return_value={"ACTIVE": 3, "INACTIVE": 0, "TOTAL": 3}),
            patch("services.dashboard_service.get_recent_activity", return_value=[]),
            patch("services.performance_service.get_business_financial_timeline", return_value=[]),
            patch('services.maintenance_service.get_servicing_schedules', return_value=[]),
            patch("services.preset_service.get_reporting_baseline_date", return_value=date(2026, 10, 1)),
            patch("services.reminder_service.get_open_reminders", return_value=[]),
            patch("services.validation_service.get_data_validation_warnings", return_value=[]),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 13)),
        ):
            app = AppTest.from_file(HOME_PAGE, default_timeout=10).run()

        self.assertEqual(len(app.exception), 0)
        labels = [metric.label for metric in app.metric]
        values = [metric.value for metric in app.metric]
        self.assertIn("Total revenue", labels)
        self.assertIn("Total expenses", labels)
        self.assertIn("Business balance", labels)
        self.assertIn("K16,200", values)
        self.assertIn("K17,000", values)
        self.assertIn("K-800", values)


if __name__ == "__main__":
    unittest.main()
