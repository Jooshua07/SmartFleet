from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.preset_service import get_reporting_baseline_date
from services.financial_rules import OPERATING_PAYMENT_TYPES


def get_period_ledger(start_date: date, end_date: date) -> list[dict]:
    if end_date < start_date:
        raise ValueError('End date must be on or after start date.')
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute('''SELECT id, transaction_date, transaction_type, direction, amount,
                description, notes FROM financial_transactions
                WHERE transaction_date BETWEEN %s AND %s
                ORDER BY transaction_date, id''', (start_date, end_date))
            return cursor.fetchall()


def summarize_ledger(rows: list[dict], opening=Decimal('0')) -> dict:
    totals = dict(opening_balance=opening, money_in=Decimal('0'), money_out=Decimal('0'),
                  collections=Decimal('0'), operating_payments=Decimal('0'), other_payments=Decimal('0'))
    breakdown = {}
    for row in rows:
        kind = row['transaction_type']
        if kind == 'TRANSFER':
            continue
        amount = row['amount']
        if row['direction'] == 'IN':
            totals['money_in'] += amount
            if kind == 'CASHING':
                totals['collections'] += amount
        elif row['direction'] == 'OUT':
            totals['money_out'] += amount
            if kind in OPERATING_PAYMENT_TYPES:
                totals['operating_payments'] += amount
            else:
                totals['other_payments'] += amount
                breakdown[kind] = breakdown.get(kind, Decimal('0')) + amount
    totals['net_movement'] = totals['money_in'] - totals['money_out']
    totals['closing_balance'] = opening + totals['net_movement']
    totals['other_payment_breakdown'] = breakdown
    return totals


def get_period_balance(start_date: date, end_date: date, ledger: list[dict] | None = None) -> dict:
    if start_date > end_date:
        raise ValueError('End date must be on or after start date.')
    baseline = get_reporting_baseline_date()
    # The approved reporting baseline is a clean-slate opening of zero.
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute('''SELECT COALESCE(SUM(CASE WHEN direction='IN' THEN amount
                ELSE -amount END),0) AS opening FROM financial_transactions
                WHERE transaction_date >= %s AND transaction_date < %s
                  AND transaction_type <> 'TRANSFER' ''', (baseline, start_date))
            opening = cursor.fetchone()['opening']
    if ledger is None:
        ledger = get_period_ledger(max(start_date, baseline), end_date) if end_date >= max(start_date, baseline) else []
    else:
        ledger = [row for row in ledger if max(start_date, baseline) <= row['transaction_date'] <= end_date]
    result = summarize_ledger(ledger, opening)
    result['baseline_date'] = baseline
    return result


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


def get_business_balance() -> dict:
    baseline_date = get_reporting_baseline_date()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN direction = 'IN' THEN amount ELSE 0 END), 0) AS money_in,
                    COALESCE(SUM(CASE WHEN direction = 'OUT' THEN amount ELSE 0 END), 0) AS money_out,
                    COALESCE(SUM(CASE WHEN transaction_type = 'CASHING' AND direction = 'IN' THEN amount ELSE 0 END), 0)
                        AS collections,
                    COALESCE(SUM(CASE WHEN transaction_type IN ('EXPENSE','DRIVER_SALARY','TRANSFER_FEE','OTHER')
                                      AND direction = 'OUT' THEN amount ELSE 0 END), 0)
                        AS operating_payments,
                    COALESCE(SUM(CASE WHEN transaction_type IN ('OWNER_LOAN','LOAN_RECEIVED')
                                      AND direction = 'IN' THEN amount ELSE 0 END), 0)
                        AS financing_in,
                    COALESCE(SUM(CASE WHEN transaction_type IN ('LOAN_REPAYMENT','OWNER_LOAN_REPAYMENT','OWNER_DRAWING')
                                      AND direction = 'OUT' THEN amount ELSE 0 END), 0)
                        AS financing_out
                FROM financial_transactions
                WHERE transaction_date >= %s;
                """,
                (baseline_date,),
            )
            summary = cursor.fetchone()

    money_in = summary["money_in"] or Decimal("0")
    money_out = summary["money_out"] or Decimal("0")
    return {
        "baseline_date": baseline_date,
        "money_in": money_in,
        "money_out": money_out,
        "business_balance": money_in - money_out,
        "collections": summary["collections"] or Decimal("0"),
        "operating_payments": summary["operating_payments"] or Decimal("0"),
        "financing_in": summary["financing_in"] or Decimal("0"),
        "financing_out": summary["financing_out"] or Decimal("0"),
    }


def get_business_ledger(limit: int = 30) -> list[dict]:
    baseline_date = get_reporting_baseline_date()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    ft.id,
                    ft.transaction_date,
                    ft.transaction_type,
                    ft.direction,
                    ft.amount,
                    CASE
                        WHEN ft.direction = 'IN' THEN ft.amount
                        ELSE -ft.amount
                    END AS signed_amount,
                    CASE
                        WHEN ft.transaction_type = 'CASHING' THEN 'Collection'
                        WHEN ft.transaction_type = 'EXPENSE' THEN 'Operating expense'
                        WHEN ft.transaction_type = 'DRIVER_SALARY' THEN 'Payroll'
                        WHEN ft.transaction_type = 'DRIVER_ADVANCE' THEN 'Recoverable advance'
                        WHEN ft.transaction_type = 'OWNER_DRAWING' THEN 'Owner drawing'
                        WHEN ft.transaction_type IN ('OWNER_LOAN','LOAN_RECEIVED') THEN 'Financing received'
                        WHEN ft.transaction_type IN ('LOAN_REPAYMENT','OWNER_LOAN_REPAYMENT') THEN 'Financing payment'
                        WHEN ft.transaction_type = 'TRANSFER_FEE' THEN 'Transfer fee'
                        WHEN ft.transaction_type = 'TRANSFER' THEN 'Transfer'
                        ELSE 'Other'
                    END AS classification,
                    ft.description,
                    ft.notes,
                    fa.name AS account_name,
                    fa.account_type
                FROM financial_transactions ft
                JOIN financial_accounts fa ON fa.id = ft.account_id
                WHERE ft.transaction_date >= %s
                ORDER BY ft.transaction_date DESC, ft.id DESC
                LIMIT %s;
                """,
                (baseline_date, limit),
            )
            return cursor.fetchall()

