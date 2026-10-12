from datetime import date

from psycopg.rows import dict_row

from database.connection import get_connection


def get_expense_export(start_date: date, end_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    e.expense_date,
                    ec.name AS category,
                    e.amount,
                    e.description,
                    e.vendor_name,
                    e.reference_number,
                    e.scope,
                    b.registration_number AS bus,
                    fa.name AS paid_from,
                    e.notes
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN buses b ON b.id = e.bus_id
                LEFT JOIN financial_accounts fa ON fa.id = e.financial_account_id
                WHERE e.expense_date BETWEEN %s AND %s
                ORDER BY e.expense_date, e.id;
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()


def get_collection_export(start_date: date, end_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    c.collection_date,
                    b.registration_number AS bus,
                    r.normal_days,
                    r.normal_daily_rate,
                    r.sunday_days,
                    r.sunday_rate,
                    r.expected_amount,
                    r.actual_amount,
                    r.variance,
                    r.explanation,
                    fa.name AS paid_into,
                    c.notes AS collection_notes,
                    r.notes AS bus_notes
                FROM remittance_collections c
                JOIN remittances r ON r.collection_id = c.id
                JOIN buses b ON b.id = r.bus_id
                JOIN financial_accounts fa ON fa.id = c.financial_account_id
                WHERE c.collection_date BETWEEN %s AND %s
                ORDER BY c.collection_date, b.registration_number;
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()


def get_balance_export() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    fa.name,
                    fa.account_type,
                    fa.opening_balance,
                    fa.opening_balance
                        + COALESCE(SUM(
                            CASE
                                WHEN ft.direction = 'IN' THEN ft.amount
                                WHEN ft.direction = 'OUT' THEN -ft.amount
                                ELSE 0
                            END
                        ), 0) AS calculated_balance
                FROM financial_accounts fa
                LEFT JOIN financial_transactions ft ON ft.account_id = fa.id
                WHERE fa.active = TRUE
                GROUP BY fa.id
                ORDER BY fa.id;
                """
            )
            return cursor.fetchall()
