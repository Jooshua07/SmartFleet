from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.financial_rules import OPERATING_EXPENSE_PREDICATE


def get_bus_contribution_summary(start_date: date, end_date: date) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
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
                    JOIN expense_categories ec ON ec.id = e.category_id
                    LEFT JOIN financial_transactions ft ON ft.id = e.financial_transaction_id
                    WHERE e.scope = 'BUS'
                      AND e.expense_date BETWEEN %s AND %s
                      AND {OPERATING_EXPENSE_PREDICATE}
                    GROUP BY e.bus_id
                ),
                allocated_expenses AS (
                    SELECT
                        ea.bus_id,
                        SUM(ea.allocated_amount) AS allocated_costs
                    FROM expense_allocations ea
                    JOIN expenses e ON e.id = ea.expense_id
                    JOIN expense_categories ec ON ec.id = e.category_id
                    LEFT JOIN financial_transactions ft ON ft.id = e.financial_transaction_id
                    WHERE e.scope = 'MULTI_BUS'
                      AND e.expense_date BETWEEN %s AND %s
                      AND {OPERATING_EXPENSE_PREDICATE}
                    GROUP BY ea.bus_id
                ),
                salary_assignments AS (
                    SELECT
                        ds.id AS salary_id,
                        ds.prorated_salary,
                        da.bus_id
                    FROM driver_salaries ds
                    JOIN driver_assignments da
                        ON da.employment_id = ds.employment_id
                       AND da.assignment_type = 'PERMANENT'
                       AND da.start_date <= (make_date(ds.salary_year, ds.salary_month, 1)
                            + INTERVAL '1 month - 1 day')::date
                       AND (da.end_date IS NULL OR da.end_date >= make_date(ds.salary_year, ds.salary_month, 1))
                    WHERE ds.status <> 'CANCELLED'
                      AND make_date(ds.salary_year, ds.salary_month, 1) BETWEEN %s AND %s
                ),
                unique_salary_bus AS (
                    SELECT
                        salary_id,
                        MIN(bus_id) AS bus_id,
                        MIN(prorated_salary) AS salary_cost
                    FROM salary_assignments
                    GROUP BY salary_id
                    HAVING COUNT(DISTINCT bus_id) = 1
                ),
                salary_by_bus AS (
                    SELECT bus_id, SUM(salary_cost) AS salary_costs
                    FROM unique_salary_bus
                    GROUP BY bus_id
                )
                SELECT
                    b.id AS bus_id,
                    b.registration_number,
                    b.status,
                    COALESCE(rb.recorded_revenue, 0) AS recorded_revenue,
                    COALESCE(rb.confirmed_revenue, 0) AS confirmed_revenue,
                    COALESCE(rb.estimated_revenue, 0) AS estimated_revenue,
                    COALESCE(de.direct_costs, 0) + COALESCE(sb.salary_costs, 0) AS direct_costs,
                    COALESCE(ae.allocated_costs, 0) AS allocated_costs,
                    COALESCE(de.direct_costs, 0) + COALESCE(ae.allocated_costs, 0)
                        + COALESCE(sb.salary_costs, 0) AS attributed_costs,
                    COALESCE(rb.recorded_revenue, 0)
                        - COALESCE(de.direct_costs, 0)
                        - COALESCE(ae.allocated_costs, 0)
                        - COALESCE(sb.salary_costs, 0) AS recorded_contribution
                FROM buses b
                LEFT JOIN revenue_by_bus rb ON rb.bus_id = b.id
                LEFT JOIN direct_expenses de ON de.bus_id = b.id
                LEFT JOIN allocated_expenses ae ON ae.bus_id = b.id
                LEFT JOIN salary_by_bus sb ON sb.bus_id = b.id
                ORDER BY b.registration_number;
                """,
                (
                    start_date,
                    end_date,
                    start_date,
                    end_date,
                    start_date,
                    end_date,
                    start_date,
                    end_date,
                ),
            )
            buses = cursor.fetchall()

            cursor.execute(
                f"""
                WITH general_expenses AS (
                    SELECT COALESCE(SUM(e.amount), 0) AS amount
                    FROM expenses e
                    JOIN expense_categories ec ON ec.id = e.category_id
                    LEFT JOIN financial_transactions ft ON ft.id = e.financial_transaction_id
                    WHERE e.scope = 'GENERAL'
                      AND e.expense_date BETWEEN %s AND %s
                      AND {OPERATING_EXPENSE_PREDICATE}
                ),
                salary_ids_with_one_bus AS (
                    SELECT ds.id
                    FROM driver_salaries ds
                    JOIN driver_assignments da
                        ON da.employment_id = ds.employment_id
                       AND da.assignment_type = 'PERMANENT'
                       AND da.start_date <= (make_date(ds.salary_year, ds.salary_month, 1)
                            + INTERVAL '1 month - 1 day')::date
                       AND (da.end_date IS NULL OR da.end_date >= make_date(ds.salary_year, ds.salary_month, 1))
                    WHERE ds.status <> 'CANCELLED'
                      AND make_date(ds.salary_year, ds.salary_month, 1) BETWEEN %s AND %s
                    GROUP BY ds.id
                    HAVING COUNT(DISTINCT da.bus_id) = 1
                ),
                unallocated_salaries AS (
                    SELECT COALESCE(SUM(ds.prorated_salary), 0) AS amount
                    FROM driver_salaries ds
                    WHERE ds.status <> 'CANCELLED'
                      AND make_date(ds.salary_year, ds.salary_month, 1) BETWEEN %s AND %s
                      AND NOT EXISTS (
                        SELECT 1
                        FROM salary_ids_with_one_bus one_bus
                        WHERE one_bus.id = ds.id
                      )
                )
                SELECT general_expenses.amount + unallocated_salaries.amount AS shared_general_costs
                FROM general_expenses, unallocated_salaries;
                """,
                (start_date, end_date, start_date, end_date, start_date, end_date),
            )
            shared = cursor.fetchone()

    return {
        "buses": buses,
        "shared_general_costs": shared["shared_general_costs"] or Decimal("0"),
    }


def get_bus_account_detail(bus_id: int, start_date: date, end_date: date) -> dict:
    from services.bus_account_detail_service import load_bus_detail

    return load_bus_detail(bus_id, start_date, end_date)
