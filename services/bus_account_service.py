from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection


def get_bus_contribution_summary(start_date: date, end_date: date) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                WITH revenue_by_bus AS (
                    SELECT
                        r.bus_id,
                        SUM(r.actual_amount) AS recorded_revenue,
                        SUM(CASE
                            WHEN r.allocation_provenance = 'CONFIRMED_ACTUAL'
                            THEN r.actual_amount ELSE 0
                        END) AS confirmed_revenue,
                        SUM(CASE
                            WHEN r.allocation_provenance <> 'CONFIRMED_ACTUAL'
                            THEN r.actual_amount ELSE 0
                        END) AS estimated_revenue
                    FROM remittances r
                    JOIN remittance_collections c ON c.id = r.collection_id
                    WHERE c.collection_date BETWEEN %s AND %s
                    GROUP BY r.bus_id
                ),
                direct_expenses AS (
                    SELECT
                        e.bus_id,
                        SUM(e.amount) AS direct_costs
                    FROM expenses e
                    WHERE e.scope = 'BUS'
                      AND e.expense_date BETWEEN %s AND %s
                    GROUP BY e.bus_id
                ),
                allocated_expenses AS (
                    SELECT
                        ea.bus_id,
                        SUM(ea.allocated_amount) AS allocated_costs
                    FROM expense_allocations ea
                    JOIN expenses e ON e.id = ea.expense_id
                    WHERE e.scope = 'MULTI_BUS'
                      AND e.expense_date BETWEEN %s AND %s
                    GROUP BY ea.bus_id
                )
                SELECT
                    b.id AS bus_id,
                    b.registration_number,
                    b.status,
                    COALESCE(rb.recorded_revenue, 0) AS recorded_revenue,
                    COALESCE(rb.confirmed_revenue, 0) AS confirmed_revenue,
                    COALESCE(rb.estimated_revenue, 0) AS estimated_revenue,
                    COALESCE(de.direct_costs, 0) AS direct_costs,
                    COALESCE(ae.allocated_costs, 0) AS allocated_costs,
                    COALESCE(de.direct_costs, 0) + COALESCE(ae.allocated_costs, 0) AS attributed_costs,
                    COALESCE(rb.recorded_revenue, 0)
                        - COALESCE(de.direct_costs, 0)
                        - COALESCE(ae.allocated_costs, 0) AS recorded_contribution
                FROM buses b
                LEFT JOIN revenue_by_bus rb ON rb.bus_id = b.id
                LEFT JOIN direct_expenses de ON de.bus_id = b.id
                LEFT JOIN allocated_expenses ae ON ae.bus_id = b.id
                ORDER BY b.registration_number;
                """,
                (start_date, end_date, start_date, end_date, start_date, end_date),
            )
            buses = cursor.fetchall()

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS shared_general_costs
                FROM expenses
                WHERE scope = 'GENERAL'
                  AND expense_date BETWEEN %s AND %s;
                """,
                (start_date, end_date),
            )
            shared = cursor.fetchone()

    return {
        "buses": buses,
        "shared_general_costs": shared["shared_general_costs"] or Decimal("0"),
    }


def get_bus_account_detail(bus_id: int, start_date: date, end_date: date) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, registration_number, status
                FROM buses
                WHERE id = %s;
                """,
                (bus_id,),
            )
            bus = cursor.fetchone()
            if bus is None:
                raise ValueError("Bus not found.")

            cursor.execute(
                """
                WITH activity AS (
                    SELECT
                        DATE_TRUNC('month', c.collection_date)::date AS month,
                        SUM(r.actual_amount) AS revenue,
                        0::numeric AS costs
                    FROM remittances r
                    JOIN remittance_collections c ON c.id = r.collection_id
                    WHERE r.bus_id = %s
                      AND c.collection_date BETWEEN %s AND %s
                    GROUP BY DATE_TRUNC('month', c.collection_date)::date
                    UNION ALL
                    SELECT
                        DATE_TRUNC('month', e.expense_date)::date AS month,
                        0::numeric AS revenue,
                        SUM(e.amount) AS costs
                    FROM expenses e
                    WHERE e.bus_id = %s
                      AND e.scope = 'BUS'
                      AND e.expense_date BETWEEN %s AND %s
                    GROUP BY DATE_TRUNC('month', e.expense_date)::date
                    UNION ALL
                    SELECT
                        DATE_TRUNC('month', e.expense_date)::date AS month,
                        0::numeric AS revenue,
                        SUM(ea.allocated_amount) AS costs
                    FROM expense_allocations ea
                    JOIN expenses e ON e.id = ea.expense_id
                    WHERE ea.bus_id = %s
                      AND e.scope = 'MULTI_BUS'
                      AND e.expense_date BETWEEN %s AND %s
                    GROUP BY DATE_TRUNC('month', e.expense_date)::date
                )
                SELECT
                    month,
                    SUM(revenue) AS recorded_revenue,
                    SUM(costs) AS attributed_costs,
                    SUM(revenue) - SUM(costs) AS recorded_contribution
                FROM activity
                GROUP BY month
                ORDER BY month;
                """,
                (bus_id, start_date, end_date, bus_id, start_date, end_date, bus_id, start_date, end_date),
            )
            trend = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    ec.name AS category_name,
                    SUM(CASE
                        WHEN e.scope = 'BUS' THEN e.amount
                        ELSE ea.allocated_amount
                    END) AS amount
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN expense_allocations ea ON ea.expense_id = e.id
                WHERE e.expense_date BETWEEN %s AND %s
                  AND (
                    (e.scope = 'BUS' AND e.bus_id = %s)
                    OR
                    (e.scope = 'MULTI_BUS' AND ea.bus_id = %s)
                  )
                GROUP BY ec.name
                ORDER BY amount DESC, ec.name;
                """,
                (start_date, end_date, bus_id, bus_id),
            )
            costs_by_category = cursor.fetchall()

            cursor.execute(
                """
                (
                    SELECT
                        c.collection_date AS transaction_date,
                        'Recorded revenue' AS transaction_group,
                        COALESCE(c.notes, 'Cashing recorded') AS title,
                        r.actual_amount AS amount,
                        r.allocation_provenance AS detail
                    FROM remittances r
                    JOIN remittance_collections c ON c.id = r.collection_id
                    WHERE r.bus_id = %s
                      AND c.collection_date BETWEEN %s AND %s
                )
                UNION ALL
                (
                    SELECT
                        e.expense_date AS transaction_date,
                        'Attributed cost' AS transaction_group,
                        e.description AS title,
                        CASE
                            WHEN e.scope = 'BUS' THEN e.amount
                            ELSE ea.allocated_amount
                        END AS amount,
                        ec.name AS detail
                    FROM expenses e
                    JOIN expense_categories ec ON ec.id = e.category_id
                    LEFT JOIN expense_allocations ea ON ea.expense_id = e.id
                    WHERE e.expense_date BETWEEN %s AND %s
                      AND (
                        (e.scope = 'BUS' AND e.bus_id = %s)
                        OR
                        (e.scope = 'MULTI_BUS' AND ea.bus_id = %s)
                      )
                )
                ORDER BY transaction_date DESC
                LIMIT 12;
                """,
                (bus_id, start_date, end_date, start_date, end_date, bus_id, bus_id),
            )
            recent_transactions = cursor.fetchall()

    return {
        "bus": bus,
        "trend": trend,
        "costs_by_category": costs_by_category,
        "recent_transactions": recent_transactions,
    }
