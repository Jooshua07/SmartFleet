import unittest

from services.bus_service import get_all_buses


class BusServiceTests(unittest.TestCase):
    def test_get_all_buses_returns_rows_with_expected_shape(self):
        buses = get_all_buses()

        self.assertIsInstance(buses, list)
        for bus in buses:
            self.assertIn("id", bus)
            self.assertIn("registration_number", bus)
            self.assertIn("route_name", bus)
            self.assertIn("status", bus)


if __name__ == "__main__":
    unittest.main()
