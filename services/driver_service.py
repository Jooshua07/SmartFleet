from datetime import date

from psycopg.rows import dict_row

from database.connection import get_connection


def get_available_driver_employments(on_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    de.id AS employment_id,
                    d.full_name,
                    de.start_date,
                    de.monthly_salary
                FROM driver_employments de
                JOIN drivers d ON d.id = de.driver_id
                WHERE de.status = 'ACTIVE'
                  AND de.start_date <= %s
                  AND (de.end_date IS NULL OR de.end_date >= %s)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM driver_assignments da
                      WHERE da.employment_id = de.id
                        AND da.status = 'ACTIVE'
                        AND da.assignment_type = 'PERMANENT'
                        AND da.start_date <= %s
                        AND (da.end_date IS NULL OR da.end_date >= %s)
                  )
                ORDER BY d.full_name;
                """,
                (on_date, on_date, on_date, on_date),
            )
            return cursor.fetchall()


def get_drivers_overview() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    d.id,
                    d.full_name,
                    d.phone,
                    de.id AS employment_id,
                    de.status AS employment_status,
                    b.registration_number AS assigned_bus
                FROM drivers d
                LEFT JOIN driver_employments de
                    ON de.driver_id = d.id
                   AND de.status = 'ACTIVE'
                LEFT JOIN driver_assignments da
                    ON da.employment_id = de.id
                   AND da.status = 'ACTIVE'
                LEFT JOIN buses b ON b.id = da.bus_id
                ORDER BY d.full_name;
                """
            )
            return cursor.fetchall()

