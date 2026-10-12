from datetime import date
import unittest

from services.bus_service import count_active_days_from_history, set_bus_status, update_bus


class FleetHistoryTests(unittest.TestCase):
    def test_mid_period_deactivation_counts_only_active_days(self):
        history = [
            {
                "status": "ACTIVE",
                "effective_from": date(2026, 10, 1),
                "effective_to": date(2026, 10, 1),
            },
            {
                "status": "INACTIVE",
                "effective_from": date(2026, 10, 2),
                "effective_to": None,
            },
        ]

        active_days = count_active_days_from_history(
            history,
            date(2026, 10, 1),
            date(2026, 10, 3),
        )

        self.assertEqual(active_days, 1)

    def test_reactivation_counts_later_active_days(self):
        history = [
            {
                "status": "ACTIVE",
                "effective_from": date(2026, 10, 1),
                "effective_to": date(2026, 10, 1),
            },
            {
                "status": "INACTIVE",
                "effective_from": date(2026, 10, 2),
                "effective_to": date(2026, 10, 2),
            },
            {
                "status": "ACTIVE",
                "effective_from": date(2026, 10, 3),
                "effective_to": None,
            },
        ]

        active_days = count_active_days_from_history(
            history,
            date(2026, 10, 1),
            date(2026, 10, 3),
        )

        self.assertEqual(active_days, 2)

    def test_set_bus_status_rejects_unknown_status_before_database_write(self):
        with self.assertRaisesRegex(ValueError, "Active or Deactivated"):
            set_bus_status(1, "IN_GARAGE", date(2026, 10, 12))

    def test_update_bus_requires_route_effective_date(self):
        with self.assertRaisesRegex(ValueError, "Route effective date is required"):
            update_bus(1, "ABC123", 1, None)


if __name__ == "__main__":
    unittest.main()

