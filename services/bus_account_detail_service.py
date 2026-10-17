"""Detail activity uses exactly the same expense and earned-salary attribution as the summary."""

from psycopg import sql
from psycopg.rows import dict_row

from database.connection import get_connection
from services.financial_rules import OPERATING_EXPENSE_PREDICATE

COST_ACTIVITY = sql.SQL("""
WITH salary_bus AS (
    SELECT ds.id, MIN(da.bus_id) AS bus_id
    FROM driver_salaries ds JOIN driver_assignments da ON da.employment_id=ds.employment_id
      AND da.assignment_type='PERMANENT'
      AND da.start_date <= (make_date(ds.salary_year,ds.salary_month,1)+INTERVAL '1 month - 1 day')::date
      AND (da.end_date IS NULL OR da.end_date >= make_date(ds.salary_year,ds.salary_month,1))
    WHERE ds.status <> 'CANCELLED'
    GROUP BY ds.id HAVING COUNT(DISTINCT da.bus_id)=1
), costs AS (
    SELECT e.id, e.expense_date AS transaction_date, e.bus_id,
           e.amount, e.description AS title, ec.name AS category_name
    FROM expenses e JOIN expense_categories ec ON ec.id=e.category_id
    LEFT JOIN financial_transactions ft ON ft.id=e.financial_transaction_id
    WHERE e.scope='BUS' AND {OPERATING_EXPENSE_PREDICATE}
    UNION ALL
    SELECT e.id,e.expense_date,ea.bus_id,ea.allocated_amount,e.description,ec.name
    FROM expenses e JOIN expense_allocations ea ON ea.expense_id=e.id
    JOIN expense_categories ec ON ec.id=e.category_id
    LEFT JOIN financial_transactions ft ON ft.id=e.financial_transaction_id
    WHERE e.scope='MULTI_BUS' AND {OPERATING_EXPENSE_PREDICATE}
    UNION ALL
    SELECT ds.id,make_date(ds.salary_year,ds.salary_month,1),sb.bus_id,
           ds.prorated_salary,'Earned driver salary','Driver Salaries'
    FROM driver_salaries ds JOIN salary_bus sb ON sb.id=ds.id
), selected_costs AS (
    SELECT * FROM costs WHERE bus_id=%s AND transaction_date BETWEEN %s AND %s
), revenues AS (
    SELECT c.collection_date AS transaction_date,r.actual_amount AS amount,
           COALESCE(c.notes,'Cashing recorded') AS title,r.allocation_provenance AS detail
    FROM remittances r JOIN remittance_collections c ON c.id=r.collection_id
    WHERE r.bus_id=%s AND c.collection_date BETWEEN %s AND %s
)
""").format(OPERATING_EXPENSE_PREDICATE=sql.SQL(OPERATING_EXPENSE_PREDICATE))


def load_bus_detail(bus_id, start_date, end_date):
    params = (bus_id, start_date, end_date, bus_id, start_date, end_date)
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT id,registration_number,status FROM buses WHERE id=%s", (bus_id,))
            bus = cursor.fetchone()
            if bus is None:
                raise ValueError("Bus not found.")
            cursor.execute(
                COST_ACTIVITY
                + sql.SQL("""
                , activity AS (
                    SELECT transaction_date,amount AS revenue,0::numeric AS costs FROM revenues
                    UNION ALL SELECT transaction_date,0,amount FROM selected_costs
                ) SELECT date_trunc('month',transaction_date)::date AS month,
                    SUM(revenue) AS recorded_revenue,SUM(costs) AS attributed_costs,
                    SUM(revenue)-SUM(costs) AS recorded_contribution
                FROM activity GROUP BY month ORDER BY month
            """),
                params,
            )
            trend = cursor.fetchall()
            cursor.execute(
                COST_ACTIVITY
                + sql.SQL("""SELECT category_name,SUM(amount) AS amount
                FROM selected_costs GROUP BY category_name ORDER BY amount DESC,category_name"""),
                params,
            )
            categories = cursor.fetchall()
            cursor.execute(
                COST_ACTIVITY
                + sql.SQL("""
                SELECT transaction_date,'Recorded revenue' AS transaction_group,title,amount,detail FROM revenues
                UNION ALL SELECT transaction_date,'Attributed cost',title,amount,category_name FROM selected_costs
                ORDER BY transaction_date DESC LIMIT 20
            """),
                params,
            )
            recent = cursor.fetchall()
    return {
        "bus": bus,
        "trend": trend,
        "costs_by_category": categories,
        "recent_transactions": recent,
    }
