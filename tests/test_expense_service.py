from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from services.expense_service import (
    _clean_expense_title,
    is_restricted_expense_category,
    record_business_expense,
    update_business_expense,
)


class FakeCursor:
    def __init__(self, fetchone_rows=None):
        self.fetchone_rows = list(fetchone_rows or [])
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


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, row_factory=None):
        return self.fake_cursor


class ExpenseServiceValidationTests(unittest.TestCase):
    def test_record_expense_requires_positive_amount(self):
        with self.assertRaisesRegex(ValueError, "Amount must be greater than zero"):
            record_business_expense(
                expense_date=date(2026, 10, 12),
                category_id=1,
                amount=0,
                description="Fuel",
                financial_account_id=1,
            )

    def test_record_expense_requires_description(self):
        with self.assertRaisesRegex(ValueError, "Expense title is required"):
            record_business_expense(
                expense_date=date(2026, 10, 12),
                category_id=1,
                amount=100,
                description=" ",
                financial_account_id=1,
            )

    def test_record_expense_requires_bus_for_bus_scope(self):
        with self.assertRaisesRegex(ValueError, "Choose a bus"):
            record_business_expense(
                expense_date=date(2026, 10, 12),
                category_id=1,
                amount=100,
                description="Repair",
                financial_account_id=1,
                scope="BUS",
            )

    def test_update_expense_blocks_general_scope_with_bus_id(self):
        with self.assertRaisesRegex(ValueError, "General expenses cannot be linked"):
            update_business_expense(
                expense_id=1,
                expense_date=date(2026, 10, 12),
                category_id=1,
                amount=100,
                description="Office",
                financial_account_id=1,
                scope="GENERAL",
                bus_id=1,
            )

    def test_expense_title_limit_blocks_long_human_titles(self):
        with self.assertRaisesRegex(ValueError, "five words or fewer"):
            _clean_expense_title("one two three four five six")

        with self.assertRaisesRegex(ValueError, "35 characters"):
            _clean_expense_title("A very long title beyond allowed text")

    def test_existing_long_title_can_be_preserved_without_truncation(self):
        title = "This old expense title is too long"

        self.assertEqual(_clean_expense_title(title, existing_title=title), title)

    def test_restricted_financial_categories_are_not_ordinary_expenses(self):
        self.assertTrue(is_restricted_expense_category("Loan Repayments"))
        self.assertTrue(is_restricted_expense_category("Driver Advances"))
        self.assertTrue(is_restricted_expense_category("Owner Drawings"))

    def test_record_general_expense_uses_default_business_account(self):
        cursor = FakeCursor(
            fetchone_rows=[
                {"id": 2, "name": "Parts"},
                {"id": 9},
                {"id": 20},
                {
                    "id": 30,
                    "expense_date": date(2026, 10, 12),
                    "amount": Decimal("3000.00"),
                    "description": "Brake Pads",
                },
            ]
        )

        with (
            patch("services.expense_service.get_default_business_payment_account", return_value={"id": 9}),
            patch("services.expense_service.get_connection", return_value=FakeConnection(cursor)),
        ):
            expense = record_business_expense(
                expense_date=date(2026, 10, 12),
                category_id=2,
                amount=3000,
                description="Brake Pads",
            )

        self.assertEqual(expense["id"], 30)
        ledger_calls = [call for call in cursor.executed if "INSERT INTO financial_transactions" in call[0]]
        self.assertEqual(len(ledger_calls), 1)
        self.assertEqual(ledger_calls[0][1][0], 9)

    def test_restricted_category_rejects_before_ledger_insert(self):
        cursor = FakeCursor(fetchone_rows=[{"id": 7, "name": "Loan Repayments"}])

        with (
            patch("services.expense_service.get_default_business_payment_account", return_value={"id": 9}),
            patch("services.expense_service.get_connection", return_value=FakeConnection(cursor)),
            self.assertRaisesRegex(ValueError, "loan repayment workflow"),
        ):
            record_business_expense(
                expense_date=date(2026, 10, 12),
                category_id=7,
                amount=15000,
                description="Loan Payment",
            )

        self.assertFalse(any("INSERT INTO financial_transactions" in call[0] for call in cursor.executed))

    def test_update_scope_keeps_one_existing_financial_payment(self):
        cursor = FakeCursor(
            fetchone_rows=[
                {
                    "financial_transaction_id": 44,
                    "payment_source": "BUSINESS_ACCOUNT",
                    "description": "Brake Pads",
                },
                {"id": 2, "name": "Parts"},
                {"id": 9},
                {"id": 1},
                {"id": 44},
                {
                    "id": 30,
                    "expense_date": date(2026, 10, 12),
                    "amount": Decimal("3000.00"),
                    "description": "Brake Pads",
                },
            ]
        )

        with (
            patch("services.expense_service.get_default_business_payment_account", return_value={"id": 9}),
            patch("services.expense_service.get_connection", return_value=FakeConnection(cursor)),
        ):
            update_business_expense(
                expense_id=30,
                expense_date=date(2026, 10, 12),
                category_id=2,
                amount=3000,
                description="Brake Pads",
                scope="BUS",
                bus_id=1,
            )

        self.assertFalse(any("INSERT INTO financial_transactions" in call[0] for call in cursor.executed))
        self.assertTrue(any("UPDATE financial_transactions" in call[0] for call in cursor.executed))


if __name__ == "__main__":
    unittest.main()
