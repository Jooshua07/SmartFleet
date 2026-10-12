from datetime import date

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import clean_optional_text, clean_required_text, parse_non_negative_amount


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


def create_driver(
    full_name: str,
    phone: str | None = None,
    address: str | None = None,
    next_of_kin_name: str | None = None,
    next_of_kin_phone: str | None = None,
    start_date: date | None = None,
    monthly_salary=2000,
    notes: str | None = None,
) -> dict:
    name = clean_required_text(full_name, "Driver name")
    employment_start = start_date or date.today()
    salary = parse_non_negative_amount(monthly_salary, "Monthly salary")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO drivers (
                    full_name,
                    phone,
                    address,
                    next_of_kin_name,
                    next_of_kin_phone,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, full_name, phone;
                """,
                (
                    name,
                    clean_optional_text(phone),
                    clean_optional_text(address),
                    clean_optional_text(next_of_kin_name),
                    clean_optional_text(next_of_kin_phone),
                    clean_optional_text(notes),
                ),
            )
            driver = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO driver_employments (
                    driver_id,
                    start_date,
                    monthly_salary,
                    status,
                    notes
                )
                VALUES (%s, %s, %s, 'ACTIVE', %s);
                """,
                (
                    driver["id"],
                    employment_start,
                    salary,
                    "Employment created from Drivers page",
                ),
            )

            return driver


def get_driver(driver_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    d.id,
                    d.full_name,
                    d.phone,
                    d.address,
                    d.next_of_kin_name,
                    d.next_of_kin_phone,
                    d.notes,
                    de.id AS employment_id,
                    de.start_date,
                    de.monthly_salary,
                    de.status AS employment_status
                FROM drivers d
                LEFT JOIN driver_employments de
                    ON de.driver_id = d.id
                   AND de.status = 'ACTIVE'
                WHERE d.id = %s;
                """,
                (driver_id,),
            )
            driver = cursor.fetchone()
            if driver is None:
                raise ValueError("Driver not found.")
            return driver


def update_driver(
    driver_id: int,
    full_name: str,
    phone: str | None = None,
    address: str | None = None,
    next_of_kin_name: str | None = None,
    next_of_kin_phone: str | None = None,
    notes: str | None = None,
) -> dict:
    name = clean_required_text(full_name, "Driver name")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE drivers
                SET full_name = %s,
                    phone = %s,
                    address = %s,
                    next_of_kin_name = %s,
                    next_of_kin_phone = %s,
                    notes = %s
                WHERE id = %s
                RETURNING id, full_name, phone;
                """,
                (
                    name,
                    clean_optional_text(phone),
                    clean_optional_text(address),
                    clean_optional_text(next_of_kin_name),
                    clean_optional_text(next_of_kin_phone),
                    clean_optional_text(notes),
                    driver_id,
                ),
            )
            driver = cursor.fetchone()
            if driver is None:
                raise ValueError("Driver not found.")
            return driver
