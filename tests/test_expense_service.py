from datetime import date
import unittest

from services.expense_service import record_business_expense, update_business_expense


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
        with self.assertRaisesRegex(ValueError, "Description is required"):
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


if __name__ == "__main__":
    unittest.main()
