from database.connection import get_connection


def test_database_connection():
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

            tables = cursor.fetchall()

            print("Connection successful!")
            print(f"Found {len(tables)} tables:")

            for table in tables:
                print(table[0])


if __name__ == "__main__":
    test_database_connection()
    