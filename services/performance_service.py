from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.preset_service import get_reporting_baseline_date
from services.finance_service import get_period_balance, get_period_ledger
from utils.reporting_periods import scheduled_chart_dates


def build_financial_timeline(start_date, end_date, daily, ledger, opening):
    from bisect import bisect_left
    dates = scheduled_chart_dates(start_date, end_date)
    activity_dates = {row['transaction_date'] for row in ledger}
    activity_dates.update(row['period_start'] for row in daily if row['revenue'] or row['operating_expenses'])
    if not dates or any(day > dates[-1] for day in activity_dates):
        dates.append(end_date)
    buckets = {day: dict(period_start=day, period_end=day, revenue=Decimal('0'),
                         operating_expenses=Decimal('0'), business_balance=Decimal('0'),
                         period_end_point=day.weekday() not in (3, 6)) for day in dates}
    for row in daily:
        index = bisect_left(dates, row['period_start'])
        if index < len(dates):
            bucket = buckets[dates[index]]
            bucket['revenue'] += row['revenue']
            bucket['operating_expenses'] += row['operating_expenses']
    for row in ledger:
        if row['transaction_type'] == 'TRANSFER':
            continue
        bucket = buckets[dates[bisect_left(dates, row['transaction_date'])]]
        bucket['business_balance'] += row['amount'] if row['direction'] == 'IN' else -row['amount']
    revenue = costs = Decimal('0')
    balance = opening
    for bucket in buckets.values():
        revenue += bucket['revenue']
        costs += bucket['operating_expenses']
        balance += bucket['business_balance']
        bucket.update(revenue=revenue, operating_expenses=costs, business_balance=balance)
    return list(buckets.values())


def get_business_financial_timeline(start_date: date, end_date: date) -> list[dict]:
    start_date = max(start_date, get_reporting_baseline_date())
    if start_date > end_date:
        return []
    return build_financial_timeline(start_date, end_date,
        get_business_performance_series(start_date, end_date),
        get_period_ledger(start_date, end_date), get_period_balance(start_date, end_date)['opening_balance'])


EXCLUDED_OPERATING_EXPENSE_CATEGORIES = {
    "Driver Advances",
    "Driver Salaries",
    "Loan Repayments",
    "Owner Drawings",
}


def get_operating_summary(start_date: date, end_date: date) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS revenue
                FROM remittance_collections
                WHERE collection_date BETWEEN %s AND %s;
                """,
                (start_date, end_date),
            )
            revenue = cursor.fetchone()["revenue"] or Decimal("0")

            cursor.execute(
                """
                SELECT COALESCE(SUM(e.amount), 0) AS expenses
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN financial_transactions ft ON ft.id = e.financial_transaction_id
                WHERE e.expense_date BETWEEN %s AND %s
                  AND ec.name <> ALL(%s)
                  AND (
                    e.payment_source = 'OWNER_PERSONAL'
                    OR ft.transaction_type IN ('EXPENSE', 'TRANSFER_FEE', 'OTHER')
                  );
                """,
                (start_date, end_date, list(EXCLUDED_OPERATING_EXPENSE_CATEGORIES)),
            )
            ordinary_expenses = cursor.fetchone()["expenses"] or Decimal("0")

            cursor.execute(
                """
                SELECT COALESCE(SUM(prorated_salary), 0) AS salary_costs
                FROM driver_salaries
                WHERE status <> 'CANCELLED'
                  AND make_date(salary_year, salary_month, 1) BETWEEN %s AND %s;
                """,
                (start_date, end_date),
            )
            salary_costs = cursor.fetchone()["salary_costs"] or Decimal("0")

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS other_costs
                FROM financial_transactions ft
                WHERE ft.transaction_date BETWEEN %s AND %s
                  AND ft.direction = 'OUT'
                  AND ft.transaction_type IN ('OTHER', 'TRANSFER_FEE')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM expenses e
                    WHERE e.financial_transaction_id = ft.id
                  );
                """,
                (start_date, end_date),
            )
            other_costs = cursor.fetchone()["other_costs"] or Decimal("0")

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

    expenses = ordinary_expenses + salary_costs + other_costs
    return {
        "revenue": revenue,
        "expenses": expenses,
        "pending_remittances": pending,
        "ordinary_expenses": ordinary_expenses,
        "salary_costs": salary_costs,
        "other_costs": other_costs,
    }


def _daily_points(start_date: date, end_date: date) -> dict[date, dict]:
    points = {}
    current = start_date
    while current <= end_date:
        points[current] = {
            "period_start": current,
            "period_end": current,
            "revenue": Decimal("0"),
            "operating_expenses": Decimal("0"),
            "net_profit_loss": Decimal("0"),
        }
        current += timedelta(days=1)
    return points


def _monday_start(value: date, baseline: date) -> date:
    week_start = value - timedelta(days=value.weekday())
    return max(week_start, baseline)


def _rollup_weekly(daily_points: dict[date, dict], baseline: date) -> list[dict]:
    weeks: dict[date, dict] = {}
    for day, point in daily_points.items():
        week_start = _monday_start(day, baseline)
        week = weeks.setdefault(
            week_start,
            {
                "period_start": week_start,
                "period_end": day,
                "revenue": Decimal("0"),
                "operating_expenses": Decimal("0"),
                "net_profit_loss": Decimal("0"),
            },
        )
        week["period_end"] = max(week["period_end"], day)
        week["revenue"] += point["revenue"]
        week["operating_expenses"] += point["operating_expenses"]
    for week in weeks.values():
        week["net_profit_loss"] = week["revenue"] - week["operating_expenses"]
    return [weeks[key] for key in sorted(weeks)]


def get_business_performance_series(start_date: date, end_date: date, grouping: str = "Daily") -> list[dict]:
    baseline = get_reporting_baseline_date()
    start_date = max(start_date, baseline)
    if start_date > end_date:
        return []
    points = _daily_points(start_date, end_date)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT collection_date AS activity_date, COALESCE(SUM(total_amount), 0) AS amount
                FROM remittance_collections
                WHERE collection_date BETWEEN %s AND %s
                GROUP BY collection_date;
                """,
                (start_date, end_date),
            )
            for row in cursor.fetchall():
                points[row["activity_date"]]["revenue"] += row["amount"]

            cursor.execute(
                """
                SELECT e.expense_date AS activity_date, COALESCE(SUM(e.amount), 0) AS amount
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN financial_transactions ft ON ft.id = e.financial_transaction_id
                WHERE e.expense_date BETWEEN %s AND %s
                  AND ec.name <> ALL(%s)
                  AND (
                    e.payment_source = 'OWNER_PERSONAL'
                    OR ft.transaction_type IN ('EXPENSE', 'TRANSFER_FEE', 'OTHER')
                  )
                GROUP BY e.expense_date;
                """,
                (start_date, end_date, list(EXCLUDED_OPERATING_EXPENSE_CATEGORIES)),
            )
            for row in cursor.fetchall():
                points[row["activity_date"]]["operating_expenses"] += row["amount"]

            cursor.execute(
                """
                SELECT make_date(salary_year, salary_month, 1) AS activity_date,
                       COALESCE(SUM(prorated_salary), 0) AS amount
                FROM driver_salaries
                WHERE status <> 'CANCELLED'
                  AND make_date(salary_year, salary_month, 1) BETWEEN %s AND %s
                GROUP BY make_date(salary_year, salary_month, 1);
                """,
                (start_date, end_date),
            )
            for row in cursor.fetchall():
                points[row["activity_date"]]["operating_expenses"] += row["amount"]

            cursor.execute(
                """
                SELECT transaction_date AS activity_date, COALESCE(SUM(amount), 0) AS amount
                FROM financial_transactions ft
                WHERE transaction_date BETWEEN %s AND %s
                  AND direction = 'OUT'
                  AND transaction_type IN ('OTHER', 'TRANSFER_FEE')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM expenses e
                    WHERE e.financial_transaction_id = ft.id
                  )
                GROUP BY transaction_date;
                """,
                (start_date, end_date),
            )
            for row in cursor.fetchall():
                points[row["activity_date"]]["operating_expenses"] += row["amount"]

    for point in points.values():
        point["net_profit_loss"] = point["revenue"] - point["operating_expenses"]

    if grouping == "Weekly":
        return _rollup_weekly(points, start_date)
    return [points[key] for key in sorted(points)]
