from datetime import date

from psycopg.rows import dict_row

from database.connection import get_connection


def get_collections(start_date: date, end_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.collection_date,
                    c.total_amount,
                    c.notes,
                    COUNT(r.id) AS bus_count
                FROM remittance_collections c
                LEFT JOIN remittances r ON r.collection_id = c.id
                WHERE c.collection_date BETWEEN %s AND %s
                GROUP BY c.id
                ORDER BY c.collection_date DESC, c.id DESC;
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()


def get_expenses(start_date: date, end_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    e.id,
                    e.expense_date,
                    ec.name AS category_name,
                    e.amount,
                    e.description,
                    e.scope,
                    b.registration_number
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN buses b ON b.id = e.bus_id
                WHERE e.expense_date BETWEEN %s AND %s
                ORDER BY e.expense_date DESC, e.id DESC;
                """,
                (start_date, end_date),
            )
            return cursor.fetchall()


def get_account_balances() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    fa.id,
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

