from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from services.finance_service import get_business_balance, get_business_ledger
from services.loan_service import record_unidentified_business_loan_repayment
from services.preset_service import set_cashing_rate, set_cashing_schedule_rule


class FakeCursor:
    def __init__(self, fetchone_rows=None, fetchall_rows=None):
        self.fetchone_rows = list(fetchone_rows or [])
        self.fetchall_rows = list(fetchall_rows or [])
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        if self.fetchone_rows:
            return self.fetchone_rows.pop(0)
        return None

    def fetchall(self):
        if self.fetchall_rows:
            return self.fetchall_rows.pop(0)
        return []


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, row_factory=None):
        return self.fake_cursor


class FinancialFoundationTests(unittest.TestCase):
    def test_business_balance_can_go_negative(self):
        cursor = FakeCursor(
            fetchone_rows=[
                {
                    "money_in": Decimal("1000.00"),
                    "money_out": Decimal("1500.00"),
                    "collections": Decimal("1000.00"),
                    "operating_payments": Decimal("500.00"),
                    "financing_in": Decimal("0.00"),
                    "financing_out": Decimal("1000.00"),
                }
            ]
        )

        with (
            patch("services.finance_service.get_reporting_baseline_date", return_value=date(2026, 10, 1)),
            patch("services.finance_service.get_connection", return_value=FakeConnection(cursor)),
        ):
            balance = get_business_balance()

        self.assertEqual(balance["business_balance"], Decimal("-500.00"))
        self.assertEqual(balance["financing_out"], Decimal("1000.00"))

    def test_business_balance_operating_query_excludes_driver_advances(self):
        cursor = FakeCursor(
            fetchone_rows=[
                {
                    "money_in": Decimal("0.00"),
                    "money_out": Decimal("1000.00"),
                    "collections": Decimal("0.00"),
                    "operating_payments": Decimal("0.00"),
                    "financing_in": Decimal("0.00"),
                    "financing_out": Decimal("0.00"),
                }
            ]
        )

        with (
            patch("services.finance_service.get_reporting_baseline_date", return_value=date(2026, 10, 1)),
            patch("services.finance_service.get_connection", return_value=FakeConnection(cursor)),
        ):
            get_business_balance()

        self.assertIn("'EXPENSE','DRIVER_SALARY','TRANSFER_FEE','OTHER'", cursor.executed[0][0])
        self.assertNotIn("DRIVER_ADVANCE','OTHER", cursor.executed[0][0])

    def test_loan_repayments_are_classified_as_financing_payments(self):
        cursor = FakeCursor(
            fetchall_rows=[
                [
                    {
                        "id": 1,
                        "transaction_date": date(2026, 10, 12),
                        "transaction_type": "LOAN_REPAYMENT",
                        "direction": "OUT",
                        "amount": Decimal("400.00"),
                        "signed_amount": Decimal("-400.00"),
                        "classification": "Financing payment",
                        "description": "Loan repayment",
                        "notes": None,
                        "account_name": "Airtel Money",
                        "account_type": "AIRTEL_MONEY",
                    }
                ]
            ]
        )

        with (
            patch("services.finance_service.get_reporting_baseline_date", return_value=date(2026, 10, 1)),
            patch("services.finance_service.get_connection", return_value=FakeConnection(cursor)),
        ):
            ledger = get_business_ledger()

        self.assertEqual(ledger[0]["classification"], "Financing payment")
        self.assertEqual(ledger[0]["signed_amount"], Decimal("-400.00"))

    def test_driver_advances_are_recoverable_not_operating_expenses(self):
        cursor = FakeCursor(
            fetchall_rows=[
                [
                    {
                        "id": 2,
                        "transaction_date": date(2026, 10, 12),
                        "transaction_type": "DRIVER_ADVANCE",
                        "direction": "OUT",
                        "amount": Decimal("1000.00"),
                        "signed_amount": Decimal("-1000.00"),
                        "classification": "Recoverable advance",
                        "description": "Driver advance - Felix",
                        "notes": None,
                        "account_name": "Airtel Money",
                        "account_type": "AIRTEL_MONEY",
                    }
                ]
            ]
        )

        with (
            patch("services.finance_service.get_reporting_baseline_date", return_value=date(2026, 10, 1)),
            patch("services.finance_service.get_connection", return_value=FakeConnection(cursor)),
        ):
            ledger = get_business_ledger()

        self.assertEqual(ledger[0]["classification"], "Recoverable advance")
        self.assertEqual(ledger[0]["description"], "Driver advance - Felix")

    def test_cashing_rate_update_preserves_old_rate_window(self):
        cursor = FakeCursor(
            fetchone_rows=[
                {"id": 3, "amount": Decimal("600.00"), "effective_from": date(2026, 10, 7)},
                {
                    "id": 4,
                    "rate_type": "NORMAL_DAY",
                    "amount": Decimal("700.00"),
                    "active": True,
                    "effective_from": date(2026, 10, 12),
                    "effective_to": None,
                    "notes": "New normal rate",
                },
            ]
        )

        with patch("services.preset_service.get_connection", return_value=FakeConnection(cursor)):
            rate = set_cashing_rate("NORMAL_DAY", "700", date(2026, 10, 12), "New normal rate")

        self.assertEqual(rate["amount"], Decimal("700.00"))
        update_calls = [call for call in cursor.executed if "UPDATE cashing_rates" in call[0]]
        self.assertEqual(update_calls[0][1], (date(2026, 10, 11), 3))

    def test_cashing_rate_update_rejects_overlapping_effective_date(self):
        cursor = FakeCursor(
            fetchone_rows=[
                {"id": 3, "amount": Decimal("600.00"), "effective_from": date(2026, 10, 7)},
            ]
        )

        with (
            patch("services.preset_service.get_connection", return_value=FakeConnection(cursor)),
            self.assertRaisesRegex(ValueError, "after the current active rate"),
        ):
            set_cashing_rate("NORMAL_DAY", "700", date(2026, 10, 7))

    def test_schedule_rule_requires_covered_days(self):
        with self.assertRaisesRegex(ValueError, "Choose at least one covered day"):
            set_cashing_schedule_rule(4, [], True, date(2026, 10, 12))

    def test_unidentified_loan_repayment_requires_notes(self):
        with self.assertRaisesRegex(ValueError, "Repayment notes is required"):
            record_unidentified_business_loan_repayment(
                date(2026, 10, 12),
                "400",
                1,
                "Lender",
                "",
            )


if __name__ == "__main__":
    unittest.main()

