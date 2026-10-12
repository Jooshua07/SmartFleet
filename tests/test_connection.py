import unittest

from database.connection import get_connection


class DatabaseConnectionTests(unittest.TestCase):
    def test_database_connection_has_core_tables(self):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                    """
                )
                table_names = {row[0] for row in cursor.fetchall()}

        self.assertIn("buses", table_names)
        self.assertIn("routes", table_names)
        self.assertIn("financial_accounts", table_names)


if __name__ == "__main__":
    unittest.main()
