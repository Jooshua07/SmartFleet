from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.preset_service import get_reporting_baseline_date
from services.finance_service import get_period_balance, get_period_ledger
from services.financial_rules import EXCLUDED_OPERATING_EXPENSE_CATEGORIES, OPERATING_EXPENSE_PREDICATE
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
    ledger = get_period_ledger(start_date, end_date)
    return build_financial_timeline(start_date, end_date,
        get_business_performance_series(start_date, end_date), ledger,
        get_period_balance(start_date, end_date, ledger=ledger)['opening_balance'])


def _load_operating_activity(cursor, start_date: date, end_date: date) -> list[dict]:
    cursor.execute(
        f"""
        WITH activity AS (
            SELECT collection_date AS activity_date, total_amount AS revenue,
                0::numeric AS ordinary_expenses, 0::numeric AS salary_costs, 0::numeric AS other_costs
            FROM remittance_collections WHERE collection_date BETWEEN %s AND %s
            UNION ALL
            SELECT e.expense_date, 0, e.amount, 0, 0
            FROM expenses e JOIN expense_categories ec ON ec.id=e.category_id
            LEFT JOIN financial_transactions ft ON ft.id=e.financial_transaction_id
            WHERE e.expense_date BETWEEN %s AND %s AND {OPERATING_EXPENSE_PREDICATE}
            UNION ALL
            SELECT make_date(salary_year,salary_month,1), 0, 0, prorated_salary, 0
            FROM driver_salaries WHERE status<>'CANCELLED'
                AND make_date(salary_year,salary_month,1) BETWEEN %s AND %s
            UNION ALL
            SELECT ft.transaction_date, 0, 0, 0, ft.amount
            FROM financial_transactions ft WHERE ft.transaction_date BETWEEN %s AND %s
                AND ft.direction='OUT' AND ft.transaction_type IN ('OTHER','TRANSFER_FEE')
                AND NOT EXISTS (SELECT 1 FROM expenses e WHERE e.financial_transaction_id=ft.id)
        )
        SELECT activity_date, SUM(revenue) AS revenue, SUM(ordinary_expenses) AS ordinary_expenses,
            SUM(salary_costs) AS salary_costs, SUM(other_costs) AS other_costs
        FROM activity GROUP BY activity_date ORDER BY activity_date
        """,
        (start_date, end_date) * 4,
    )
    return cursor.fetchall()


def get_operating_summary(start_date: date, end_date: date) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            activity = _load_operating_activity(cursor, start_date, end_date)
            cursor.execute(
                """
                SELECT COALESCE(SUM(expected_amount - actual_amount), 0) AS pending
                FROM remittances r JOIN remittance_collections c ON c.id=r.collection_id
                WHERE c.collection_date BETWEEN %s AND %s
                  AND expected_amount IS NOT NULL AND expected_amount > actual_amount
                """,
                (start_date, end_date),
            )
            pending = cursor.fetchone()["pending"] or Decimal("0")

    totals = {field: sum((row[field] for row in activity), Decimal("0"))
              for field in ("revenue", "ordinary_expenses", "salary_costs", "other_costs")}
    totals["expenses"] = totals["ordinary_expenses"] + totals["salary_costs"] + totals["other_costs"]
    totals["pending_remittances"] = pending
    return totals


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
            for row in _load_operating_activity(cursor, start_date, end_date):
                points[row["activity_date"]]["revenue"] = row["revenue"]
                points[row["activity_date"]]["operating_expenses"] = (
                    row["ordinary_expenses"] + row["salary_costs"] + row["other_costs"]
                )

    for point in points.values():
        point["net_profit_loss"] = point["revenue"] - point["operating_expenses"]

    if grouping == "Weekly":
        return _rollup_weekly(points, start_date)
    return [points[key] for key in sorted(points)]
