from decimal import Decimal
import unittest

from utils.dashboard_charts import build_bus_performance_chart, build_bus_performance_chart_data


class DashboardChartTests(unittest.TestCase):
    def test_bus_performance_chart_data_keeps_kwacha_scale(self):
        data = build_bus_performance_chart_data(
            [
                {
                    "registration_number": "ABC123",
                    "revenue": Decimal("6000.00"),
                    "expenses": Decimal("4000.00"),
                }
            ]
        )

        self.assertEqual(data.loc[data["Type"] == "Revenue", "Amount"].iloc[0], 6000.0)
        self.assertEqual(data.loc[data["Type"] == "Expenses", "Amount"].iloc[0], 4000.0)

    def test_bus_performance_chart_y_axis_starts_at_zero(self):
        data = build_bus_performance_chart_data(
            [
                {
                    "registration_number": "ABC123",
                    "revenue": Decimal("1000.00"),
                    "expenses": Decimal("4000.00"),
                }
            ]
        )
        spec = build_bus_performance_chart(data).to_dict()

        self.assertEqual(spec["encoding"]["y"]["scale"]["domainMin"], 0)


if __name__ == "__main__":
    unittest.main()
