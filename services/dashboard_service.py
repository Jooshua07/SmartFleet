from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection


def get_financial_summary(start_date: date, end_date: date) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(actual_amount), 0) AS revenue
                FROM remittances r
                JOIN remittance_collections c ON c.id = r.collection_id
                WHERE c.collection_date BETWEEN %s AND %s;
                """,
                (start_date, end_date),
            )
            revenue = cursor.fetchone()["revenue"] or Decimal("0")

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS expenses
                FROM expenses
                WHERE expense_date BETWEEN %s AND %s;
                """,
                (start_date, end_date),
            )
            expenses = cursor.fetchone()["expenses"] or Decimal("0")

            cursor.execute(
                """
                SELECT COALESCE(SUM(expected_amount - actual_amount), 0) AS pending
                FROM remittances r
                JOIN remittance_collections c ON c.id = r.collection_id
                WHERE c.collection_date BETWEEN %s AND %s
                  AND expected_amount IS NOT NULL
                  AND expected_amount > actual_amount;
                """,
                (start_date, end_date),
            )
            pending = cursor.fetchone()["pending"] or Decimal("0")

    return {"revenue": revenue, "expenses": expenses, "pending_remittances": pending}


def get_bus_status_counts() -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM buses
                GROUP BY status;
                """
            )
            rows = cursor.fetchall()

    counts = {"ACTIVE": 0, "INACTIVE": 0, "TOTAL": 0}
    for row in rows:
        counts[row["status"]] = row["count"]
        counts["TOTAL"] += row["count"]
    return counts


def get_bus_performance(start_date: date, end_date: date) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                WITH revenue_by_bus AS (
                    SELECT
                        r.bus_id,
                        SUM(r.actual_amount) AS revenue
                    FROM remittances r
                    JOIN remittance_collections c ON c.id = r.collection_id
                    WHERE c.collection_date BETWEEN %s AND %s
                    GROUP BY r.bus_id
                ),
                expense_by_bus AS (
                    SELECT
                        e.bus_id,
                        SUM(e.amount) AS expenses
                    FROM expenses e
                    WHERE e.scope = 'BUS'
                      AND e.expense_date BETWEEN %s AND %s
                    GROUP BY e.bus_id
                    UNION ALL
                    SELECT
                        ea.bus_id,
                        SUM(ea.allocated_amount) AS expenses
                    FROM expense_allocations ea
                    JOIN expenses e ON e.id = ea.expense_id
                    WHERE e.scope = 'MULTI_BUS'
                      AND e.expense_date BETWEEN %s AND %s
                    GROUP BY ea.bus_id
                ),
                expense_totals AS (
                    SELECT bus_id, SUM(expenses) AS expenses
                    FROM expense_by_bus
                    GROUP BY bus_id
                )
                SELECT
                    b.registration_number,
                    COALESCE(rb.revenue, 0) AS revenue,
                    COALESCE(et.expenses, 0) AS expenses
                FROM buses b
                LEFT JOIN revenue_by_bus rb ON rb.bus_id = b.id
                LEFT JOIN expense_totals et ON et.bus_id = b.id
                ORDER BY b.registration_number;
                """,
                (start_date, end_date, start_date, end_date, start_date, end_date),
            )
            return cursor.fetchall()


def get_activity_date_bounds() -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    MIN(activity_date) AS earliest_date,
                    MAX(activity_date) AS latest_date
                FROM (
                    SELECT collection_date AS activity_date
                    FROM remittance_collections
                    UNION ALL
                    SELECT expense_date AS activity_date
                    FROM expenses
                ) activity;
                """
            )
            return cursor.fetchone()


def get_recent_activity(limit: int = 5) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                (
                    SELECT
                        'Cashing recorded' AS title,
                        CONCAT('Collection total ', total_amount) AS detail,
                        total_amount AS amount,
                        collection_date AS activity_date
                    FROM remittance_collections
                )
                UNION ALL
                (
                    SELECT
                        'Expense recorded' AS title,
                        description AS detail,
                        amount,
                        expense_date AS activity_date
                    FROM expenses
                )
                UNION ALL
                (
                    SELECT
                        'Maintenance recorded' AS title,
                        description AS detail,
                        total_cost AS amount,
                        reported_date AS activity_date
                    FROM maintenance
                )
                ORDER BY activity_date DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cursor.fetchall()
