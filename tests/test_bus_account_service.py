from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from services.bus_account_service import get_bus_contribution_summary


class FakeCursor:
    def __init__(self, fetchall_rows=None, fetchone_rows=None):
        self.fetchall_rows = list(fetchall_rows or [])
        self.fetchone_rows = list(fetchone_rows or [])
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        if self.fetchall_rows:
            return self.fetchall_rows.pop(0)
        return []

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


class BusAccountServiceTests(unittest.TestCase):
    def test_bus_contribution_keeps_shared_costs_separate(self):
        cursor = FakeCursor(
            fetchall_rows=[
                [
                    {
                        "bus_id": 1,
                        "registration_number": "AIH123",
                        "status": "ACTIVE",
                        "recorded_revenue": Decimal("12000.00"),
                        "confirmed_revenue": Decimal("12000.00"),
                        "estimated_revenue": Decimal("0.00"),
                        "direct_costs": Decimal("8000.00"),
                        "allocated_costs": Decimal("0.00"),
                        "attributed_costs": Decimal("8000.00"),
                        "recorded_contribution": Decimal("4000.00"),
                    },
                    {
                        "bus_id": 2,
                        "registration_number": "AIF123",
                        "status": "ACTIVE",
                        "recorded_revenue": Decimal("9000.00"),
                        "confirmed_revenue": Decimal("9000.00"),
                        "estimated_revenue": Decimal("0.00"),
                        "direct_costs": Decimal("5000.00"),
                        "allocated_costs": Decimal("0.00"),
                        "attributed_costs": Decimal("5000.00"),
                        "recorded_contribution": Decimal("4000.00"),
                    },
                ]
            ],
            fetchone_rows=[{"shared_general_costs": Decimal("7535.00")}],
        )

        with patch("services.bus_account_service.get_connection", return_value=FakeConnection(cursor)):
            summary = get_bus_contribution_summary(date(2026, 10, 1), date(2026, 10, 31))

        self.assertEqual(summary["shared_general_costs"], Decimal("7535.00"))
        self.assertEqual(summary["buses"][0]["attributed_costs"], Decimal("8000.00"))
        self.assertEqual(summary["buses"][1]["attributed_costs"], Decimal("5000.00"))
        self.assertIn("scope = 'GENERAL'", cursor.executed[1][0])


if __name__ == "__main__":
    unittest.main()
