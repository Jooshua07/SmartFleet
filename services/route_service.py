from psycopg.rows import dict_row
from database.connection import get_connection


def get_all_routes():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT id, name, description, active
                FROM routes
                ORDER BY name;
            """)

            return cursor.fetchall()


def get_active_routes():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT id, name, description, active
                FROM routes
                WHERE active = TRUE
                ORDER BY name;
            """)

            return cursor.fetchall()


def add_route(name, description=None):
    name = name.strip()

    if not name:
        raise ValueError("Route name cannot be empty.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                INSERT INTO routes (name, description)
                VALUES (%s, %s)
                RETURNING id, name, description, active;
            """, (name, description))

            return cursor.fetchone()
