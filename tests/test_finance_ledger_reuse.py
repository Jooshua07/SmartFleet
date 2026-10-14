from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from services.finance_service import get_period_balance
from services.financial_rules import EXCLUDED_OPERATING_EXPENSE_CATEGORIES
from services.expense_service import RESTRICTED_EXPENSE_CATEGORIES
from tests.test_financial_foundation import FakeConnection, FakeCursor


class FinanceLedgerReuseTest(unittest.TestCase):
    def test_supplied_ledger_preserves_cutoff_and_skips_second_fetch(self):
        rows=[dict(transaction_date=date(2026,9,30),transaction_type='CASHING',direction='IN',amount=Decimal('999')),
              dict(transaction_date=date(2026,10,5),transaction_type='EXPENSE',direction='OUT',amount=Decimal('200')),
              dict(transaction_date=date(2026,11,1),transaction_type='CASHING',direction='IN',amount=Decimal('1000'))]
        cursor=FakeCursor(fetchone_rows=[{'opening':Decimal('50')}])
        with patch('services.finance_service.get_reporting_baseline_date',return_value=date(2026,10,1)), \
             patch('services.finance_service.get_connection',return_value=FakeConnection(cursor)), \
             patch('services.finance_service.get_period_ledger') as fetch:
            result=get_period_balance(date(2026,10,1),date(2026,10,31),ledger=rows)
        self.assertEqual(result['money_out'],200)
        self.assertEqual(result['money_in'],0)
        self.assertEqual(result['closing_balance'],-150)
        fetch.assert_not_called()

    def test_categories_match_restricted_recording_workflows(self):
        self.assertEqual(EXCLUDED_OPERATING_EXPENSE_CATEGORIES,set(RESTRICTED_EXPENSE_CATEGORIES))

    def test_invalid_range_is_rejected_even_with_empty_ledger(self):
        with self.assertRaises(ValueError):
            get_period_balance(date(2026,10,31),date(2026,10,1),ledger=[])
