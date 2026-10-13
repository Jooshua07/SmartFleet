from datetime import date
from decimal import Decimal
import unittest

from services.driver_money_service import _allocate_recovery, _month_bounds, _overlap_days


class DriverMoneyServiceTests(unittest.TestCase):
    def test_month_bounds_for_october_salary_period(self):
        start, end = _month_bounds(2026, 10)

        self.assertEqual(start, date(2026, 10, 1))
        self.assertEqual(end, date(2026, 10, 31))

    def test_mid_month_employment_start_prorates_worked_days(self):
        worked_days = _overlap_days(
            date(2026, 10, 1),
            date(2026, 10, 31),
            {"start_date": date(2026, 10, 16), "end_date": None},
        )

        self.assertEqual(worked_days, 16)

    def test_recovery_allocation_uses_oldest_advances_first(self):
        allocations = _allocate_recovery(
            [
                {"id": 1, "outstanding_amount": Decimal("600.00")},
                {"id": 2, "outstanding_amount": Decimal("500.00")},
            ],
            Decimal("1000.00"),
        )

        self.assertEqual(
            allocations,
            [
                {"advance_id": 1, "amount": Decimal("600.00")},
                {"advance_id": 2, "amount": Decimal("400.00")},
            ],
        )

    def test_recovery_allocation_rejects_more_than_outstanding(self):
        with self.assertRaisesRegex(ValueError, "could not be fully allocated"):
            _allocate_recovery([{"id": 1, "outstanding_amount": Decimal("100.00")}], Decimal("150.00"))


if __name__ == "__main__":
    unittest.main()
