from datetime import date, timedelta

from psycopg.rows import dict_row

from database.connection import get_connection


def get_due_maintenance(reference_date: date, days: int = 21) -> list[dict]:
    end_date = reference_date + timedelta(days=days)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    ms.id,
                    b.registration_number,
                    ms.schedule_name,
                    ms.next_due_date,
                    ms.interval_days
                FROM maintenance_schedules ms
                JOIN buses b ON b.id = ms.bus_id
                WHERE ms.active = TRUE
                  AND ms.next_due_date IS NOT NULL
                  AND ms.next_due_date <= %s
                ORDER BY ms.next_due_date, b.registration_number;
                """,
                (end_date,),
            )
            return cursor.fetchall()


def get_deactivated_buses() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, registration_number, updated_at, notes
                FROM buses
                WHERE status = 'INACTIVE'
                ORDER BY updated_at DESC, registration_number;
                """
            )
            return cursor.fetchall()


def get_document_expiries(reference_date: date, days: int = 30) -> list[dict]:
    end_date = reference_date + timedelta(days=days)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    bd.id,
                    b.registration_number,
                    bd.document_type,
                    bd.document_number,
                    bd.expiry_date
                FROM bus_documents bd
                JOIN buses b ON b.id = bd.bus_id
                WHERE bd.expiry_date IS NOT NULL
                  AND bd.expiry_date <= %s
                ORDER BY bd.expiry_date, b.registration_number, bd.document_type;
                """,
                (end_date,),
            )
            return cursor.fetchall()


def get_open_reminders(limit: int | None = None) -> list[dict]:
    limit_sql = "LIMIT %s" if limit else ""
    params = (limit,) if limit else ()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT
                    id,
                    reminder_type,
                    title,
                    description,
                    due_date,
                    status
                FROM reminders
                WHERE status = 'PENDING'
                ORDER BY due_date, id
                {limit_sql};
                """,
                params,
            )
            return cursor.fetchall()
