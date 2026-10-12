import unittest

from services.route_service import get_all_routes


class RouteServiceTests(unittest.TestCase):
    def test_get_all_routes_returns_rows_with_expected_shape(self):
        routes = get_all_routes()

        self.assertIsInstance(routes, list)
        for route in routes:
            self.assertIn("id", route)
            self.assertIn("name", route)
            self.assertIn("active", route)


if __name__ == "__main__":
    unittest.main()
