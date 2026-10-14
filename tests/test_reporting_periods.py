import unittest
from datetime import date
from decimal import Decimal

from utils.reporting_periods import reporting_period, scheduled_chart_dates
from services.finance_service import summarize_ledger


class ReportingPeriodsTest(unittest.TestCase):
    def test_calendar_year_boundary(self):
        self.assertEqual(reporting_period('3 Months', date(2025, 1, 1), date(2026, 1, 8)), (date(2025, 11, 1), date(2026, 1, 8)))
        self.assertEqual(reporting_period('Month', date(2026, 10, 1), date(2026, 11, 1)), (date(2026, 11, 1), date(2026, 11, 1)))

    def test_baseline_and_custom(self):
        self.assertEqual(reporting_period('6 Months', date(2026, 10, 1), date(2026, 10, 14))[0], date(2026, 10, 1))
        with self.assertRaises(ValueError):
            reporting_period('Custom', date(2026, 10, 1), start=date(2026, 10, 8), end=date(2026, 10, 1))

    def test_empty_month_carries_balance(self):
        self.assertEqual(summarize_ledger([], Decimal('-800'))['closing_balance'], Decimal('-800'))

    def test_cash_classification_and_transfers(self):
        rows = [dict(transaction_type=k, direction=d, amount=Decimal(a)) for k,d,a in [('CASHING','IN','600'),('LOAN_RECEIVED','IN','2000'),('EXPENSE','OUT','100'),('DRIVER_ADVANCE','OUT','500'),('TRANSFER','OUT','200')]]
        result = summarize_ledger(rows, Decimal('-800'))
        self.assertEqual(result['collections'], 600)
        self.assertEqual(result['other_payments'], 500)
        self.assertEqual(result['closing_balance'], 1200)

    def test_scheduled_dates(self):
        self.assertEqual(scheduled_chart_dates(date(2026,10,1), date(2026,10,11)), [date(2026,10,d) for d in (1,4,8,11)])
