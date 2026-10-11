from psycopg.rows import dict_row
from database.connection import get_connection


def get_all_buses():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT
                    b.id,
                    b.registration_number,
                    r.name AS route_name,
                    b.status,
                    b.date_acquired,
                    b.notes
                FROM buses b
                JOIN routes r ON b.route_id = r.id
                ORDER BY b.id;
            """)

            return cursor.fetchall()