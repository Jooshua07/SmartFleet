import unittest
from datetime import date
from decimal import Decimal
from services.performance_service import build_financial_timeline
from utils.dashboard_charts import build_financial_chart, build_financial_chart_data


class FinancialTimelineTest(unittest.TestCase):
    def test_between_dates_and_final_point(self):
        daily = [dict(period_start=date(2026,10,5), revenue=Decimal('0'), operating_expenses=Decimal('4000'))]
        ledger = [dict(transaction_date=date(2026,10,5), transaction_type='EXPENSE', direction='OUT', amount=Decimal('4000')),
                  dict(transaction_date=date(2026,10,14), transaction_type='LOAN_RECEIVED', direction='IN', amount=Decimal('500'))]
        series = build_financial_timeline(date(2026,10,1), date(2026,10,14), daily, ledger, Decimal('-800'))
        self.assertEqual(series[2]['operating_expenses'], 4000)
        self.assertEqual(series[2]['business_balance'], -4800)
        self.assertEqual(series[-1]['business_balance'], -4300)
        self.assertTrue(series[-1]['period_end_point'])
        self.assertEqual(series[0]['revenue'], 0)

    def test_cumulative_and_axis(self):
        daily = [dict(period_start=date(2026,10,1), revenue=Decimal('100000'), operating_expenses=Decimal('0'))]
        series = build_financial_timeline(date(2026,10,1), date(2026,10,11), daily, [], Decimal('200'))
        self.assertEqual(series[-1]['revenue'], 100000)
        data = build_financial_chart_data(series)
        spec = build_financial_chart(data).to_dict()
        self.assertEqual(set(data.Type), {'Total Revenue', 'Total Expenses', 'Business Balance'})
        self.assertNotIn('domain', spec['layer'][1]['encoding']['y']['scale'])
        self.assertEqual(spec['layer'][1]['encoding']['tooltip'][-1]['format'], ',.2f')
