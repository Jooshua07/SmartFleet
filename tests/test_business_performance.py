from datetime import date
from decimal import Decimal
import unittest

from services.performance_service import _daily_points, _rollup_weekly
from utils.dashboard_charts import build_business_performance_chart, build_business_performance_chart_data


class BusinessPerformanceTests(unittest.TestCase):
    def test_daily_points_include_zero_activity_dates(self):
        points = _daily_points(date(2026, 10, 1), date(2026, 10, 3))

        self.assertEqual(len(points), 3)
        self.assertEqual(points[date(2026, 10, 2)]["revenue"], Decimal("0"))
        self.assertEqual(points[date(2026, 10, 2)]["operating_expenses"], Decimal("0"))

    def test_weekly_rollup_uses_partial_first_week_from_baseline(self):
        points = _daily_points(date(2026, 10, 1), date(2026, 10, 8))
        points[date(2026, 10, 1)]["revenue"] = Decimal("100")
        points[date(2026, 10, 5)]["operating_expenses"] = Decimal("25")
        for point in points.values():
            point["net_profit_loss"] = point["revenue"] - point["operating_expenses"]

        weekly = _rollup_weekly(points, date(2026, 10, 1))

        self.assertEqual(weekly[0]["period_start"], date(2026, 10, 1))
        self.assertEqual(weekly[0]["period_end"], date(2026, 10, 4))
        self.assertEqual(weekly[0]["net_profit_loss"], Decimal("100"))
        self.assertEqual(weekly[1]["period_start"], date(2026, 10, 5))
        self.assertEqual(weekly[1]["net_profit_loss"], Decimal("-25"))

    def test_chart_data_has_three_business_lines_and_negative_values(self):
        chart_data = build_business_performance_chart_data(
            [
                {
                    "period_start": date(2026, 10, 1),
                    "period_end": date(2026, 10, 1),
                    "revenue": Decimal("100"),
                    "operating_expenses": Decimal("125"),
                    "net_profit_loss": Decimal("-25"),
                }
            ]
        )

        self.assertEqual(set(chart_data["Type"]), {"Revenue", "Operating Expenses", "Recorded Operating Profit/Loss"})
        self.assertIn(-25, chart_data["Amount"].tolist())
        chart = build_business_performance_chart(chart_data)
        self.assertIn("layer", chart.to_dict())


if __name__ == "__main__":
    unittest.main()
