from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRIVER_MONEY_PAGE = PROJECT_ROOT / "app_pages" / "driver_money.py"
LOANS_PAGE = PROJECT_ROOT / "app_pages" / "loans.py"
OWNER_MONEY_PAGE = PROJECT_ROOT / "app_pages" / "owner_money.py"

DRIVER_PROFILES = [
    {
        "employment_id": 7,
        "driver_id": 3,
        "driver_name": "AIG Driver",
        "start_date": date(2026, 10, 1),
        "end_date": None,
        "employment_status": "ACTIVE",
        "employment_salary": Decimal("2500.00"),
        "assigned_bus": "AIG5301",
    }
]

DRIVER_DETAIL = {
    "employment": {
        "employment_id": 7,
        "driver_id": 3,
        "driver_name": "AIG Driver",
        "start_date": date(2026, 10, 1),
        "end_date": None,
        "employment_status": "ACTIVE",
        "employment_salary": Decimal("2500.00"),
    },
    "advances": [
        {
            "id": 11,
            "advance_date": date(2026, 10, 4),
            "amount": Decimal("1000.00"),
            "recovered_amount": Decimal("0.00"),
            "outstanding_amount": Decimal("1000.00"),
            "reason": "School fees",
        }
    ],
    "salaries": [
        {
            "id": 20,
            "salary_year": 2026,
            "salary_month": 10,
            "base_salary": Decimal("2500.00"),
            "prorated_salary": Decimal("2500.00"),
            "advance_recovery": Decimal("1000.00"),
            "other_deductions": Decimal("0.00"),
            "net_salary": Decimal("1500.00"),
            "status": "PAID",
            "payment_date": date(2026, 10, 31),
            "notes": None,
        }
    ],
    "recoveries": [
        {
            "id": 30,
            "amount": Decimal("1000.00"),
            "advance_date": date(2026, 10, 4),
            "salary_year": 2026,
            "salary_month": 10,
            "salary_status": "PAID",
        }
    ],
}

SALARY_PREVIEW = {
    "worked_days": 31,
    "days_in_month": 31,
    "prorated_salary": Decimal("2500.00"),
    "suggested_recovery": Decimal("1000.00"),
    "net_salary": Decimal("1500.00"),
}

LOANS = [
    {
        "id": 4,
        "loan_name": "Carecoop loan",
        "lender": "Carecoop",
        "original_amount": Decimal("30000.00"),
        "outstanding_principal": Decimal("20000.00"),
        "default_monthly_repayment": None,
        "status": "ACTIVE",
        "notes": "Known loan from owner records.",
    }
]

REPAYMENTS = [
    {
        "id": 8,
        "repayment_date": date(2026, 10, 4),
        "amount": Decimal("15000.00"),
        "payment_source": "BUSINESS_ACCOUNT",
        "lender": "Carecoop",
    }
]

OWNER_SUMMARY = {
    "owner_balance": Decimal("30000.00"),
    "owner_funded": Decimal("30000.00"),
    "owner_repaid": Decimal("0.00"),
    "transactions": [
        {
            "transaction_date": date(2026, 10, 6),
            "transaction_type": "LOAN_TO_BUSINESS",
            "amount": Decimal("30000.00"),
            "description": "Owner paid lender directly",
        }
    ],
}


class MoneyManagementPageTests(unittest.TestCase):
    def test_driver_money_page_shows_salary_advance_and_history_views(self):
        with (
            patch("services.driver_money_service.list_driver_money_profiles", return_value=DRIVER_PROFILES),
            patch("services.driver_money_service.get_driver_money_detail", return_value=DRIVER_DETAIL),
            patch("services.driver_money_service.get_salary_preview", return_value=SALARY_PREVIEW),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 31)),
        ):
            app = AppTest.from_file(DRIVER_MONEY_PAGE, default_timeout=10)
            app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Driver", [selectbox.label for selectbox in app.selectbox])
        self.assertIn("Gross earned", [metric.label for metric in app.metric])
        self.assertIn("Outstanding advances", [subheader.value for subheader in app.subheader])
        self.assertIn("Salary history", [subheader.value for subheader in app.subheader])

    def test_driver_money_advance_mode_has_single_advance_form(self):
        with (
            patch("services.driver_money_service.list_driver_money_profiles", return_value=DRIVER_PROFILES),
            patch("services.driver_money_service.get_driver_money_detail", return_value=DRIVER_DETAIL),
            patch("services.driver_money_service.get_salary_preview", return_value=SALARY_PREVIEW),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 31)),
        ):
            app = AppTest.from_file(DRIVER_MONEY_PAGE, default_timeout=10).run()
            app.segmented_control[0].set_value("Record Advance").run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Advance date", [field.label for field in app.date_input])
        self.assertIn("Advance amount (K)", [field.label for field in app.number_input])
        self.assertIn("Reason", [field.label for field in app.text_input])

    def test_loans_page_shows_repayment_form_and_history(self):
        with (
            patch("services.loan_service.list_business_loans", return_value=LOANS),
            patch("services.loan_service.list_loan_repayments", return_value=REPAYMENTS),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 13)),
        ):
            app = AppTest.from_file(LOANS_PAGE, default_timeout=10).run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Outstanding debt", [metric.label for metric in app.metric])
        self.assertIn("Loan", [selectbox.label for selectbox in app.selectbox])
        self.assertIn("Payment source", [control.label for control in app.segmented_control])
        self.assertIn("Loan list", [subheader.value for subheader in app.subheader])
        self.assertIn("Repayment history", [subheader.value for subheader in app.subheader])

    def test_loans_add_mode_accepts_unknown_optional_terms(self):
        with (
            patch("services.loan_service.list_business_loans", return_value=LOANS),
            patch("services.loan_service.list_loan_repayments", return_value=[]),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 13)),
        ):
            app = AppTest.from_file(LOANS_PAGE, default_timeout=10).run()
            app.segmented_control[0].set_value("Add Loan").run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Loan name", [field.label for field in app.text_input])
        self.assertIn("Lender/company/association", [field.label for field in app.text_input])
        self.assertIn("Term in months", [field.label for field in app.text_input])

    def test_owner_money_page_shows_distinct_owner_workflows(self):
        with (
            patch("services.loan_service.get_owner_money_summary", return_value=OWNER_SUMMARY),
            patch("services.loan_service.list_business_loans", return_value=LOANS),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 13)),
        ):
            app = AppTest.from_file(OWNER_MONEY_PAGE, default_timeout=10).run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Owed to owner", [metric.label for metric in app.metric])
        owner_mode = next(control for control in app.segmented_control if control.label == "Owner money action")
        self.assertEqual(
            owner_mode.options,
            ["Owner Drawing", "Owner Loan to Business", "Owner Pays Business Loan", "Business Repays Owner"],
        )
        self.assertIn("Owner money history", [subheader.value for subheader in app.subheader])

    def test_owner_pays_business_loan_mode_does_not_use_business_cash_language(self):
        with (
            patch("services.loan_service.get_owner_money_summary", return_value=OWNER_SUMMARY),
            patch("services.loan_service.list_business_loans", return_value=LOANS),
            patch("utils.dates.today_lusaka", return_value=date(2026, 10, 13)),
        ):
            app = AppTest.from_file(OWNER_MONEY_PAGE, default_timeout=10).run()
            app.segmented_control[0].set_value("Owner Pays Business Loan").run()

        self.assertEqual(len(app.exception), 0)
        self.assertIn("Loan", [field.label for field in app.selectbox])
        self.assertIn("Principal paid personally (K)", [field.label for field in app.number_input])
        self.assertIn("Save personal payment", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
