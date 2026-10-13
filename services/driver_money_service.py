from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from psycopg.rows import dict_row

from database.connection import get_connection
from services.account_service import get_default_business_payment_account
from services.correction_service import record_correction_audit
from services.preset_service import get_driver_advance_limit
from utils.validation import clean_optional_text, clean_required_text, parse_non_negative_amount, parse_positive_amount


KWACHA = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(KWACHA, rounding=ROUND_HALF_UP)


def _coerce_date(value, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"{field_name} is required.")


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    if int(year) < 2000:
        raise ValueError("Salary year must be 2000 or later.")
    if int(month) not in range(1, 13):
        raise ValueError("Salary month must be January through December.")
    return date(int(year), int(month), 1), date(int(year), int(month), monthrange(int(year), int(month))[1])


def _overlap_days(start: date, end: date, employment: dict) -> int:
    period_start = max(start, employment["start_date"])
    employment_end = employment["end_date"] or end
    period_end = min(end, employment_end)
    if period_end < period_start:
        return 0
    return (period_end - period_start).days + 1


def list_driver_money_profiles() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    de.id AS employment_id,
                    d.id AS driver_id,
                    d.full_name AS driver_name,
                    de.start_date,
                    de.end_date,
                    de.status AS employment_status,
                    de.monthly_salary AS employment_salary,
                    b.registration_number AS assigned_bus
                FROM driver_employments de
                JOIN drivers d ON d.id = de.driver_id
                LEFT JOIN driver_assignments da
                    ON da.employment_id = de.id
                   AND da.status = 'ACTIVE'
                   AND da.assignment_type = 'PERMANENT'
                LEFT JOIN buses b ON b.id = da.bus_id
                ORDER BY d.full_name, de.start_date DESC;
                """
            )
            return cursor.fetchall()


def _load_employment(cursor, employment_id: int, lock: bool = False) -> dict:
    lock_clause = " FOR UPDATE" if lock else ""
    cursor.execute(
        f"""
        SELECT
            de.id AS employment_id,
            de.driver_id,
            d.full_name AS driver_name,
            de.start_date,
            de.end_date,
            de.status AS employment_status,
            de.monthly_salary AS employment_salary
        FROM driver_employments de
        JOIN drivers d ON d.id = de.driver_id
        WHERE de.id = %s
        {lock_clause};
        """,
        (employment_id,),
    )
    employment = cursor.fetchone()
    if employment is None:
        raise ValueError("Driver employment was not found.")
    return employment


def _get_effective_monthly_salary(cursor, employment: dict, period_start: date) -> Decimal:
    cursor.execute(
        """
        SELECT monthly_salary
        FROM driver_salary_presets
        WHERE active = TRUE
          AND effective_from <= %s
          AND (effective_to IS NULL OR effective_to >= %s)
          AND (driver_id = %s OR driver_id IS NULL)
        ORDER BY (driver_id IS NULL), effective_from DESC, id DESC
        LIMIT 1;
        """,
        (period_start, period_start, employment["driver_id"]),
    )
    preset = cursor.fetchone()
    if preset:
        return preset["monthly_salary"]
    return employment["employment_salary"]


def _outstanding_advances_query() -> str:
    return """
        SELECT
            a.id,
            a.employment_id,
            a.advance_date,
            a.amount,
            a.planned_repayment_amount,
            a.status,
            a.reason,
            a.notes,
            a.financial_transaction_id,
            COALESCE(SUM(CASE WHEN s.status = 'PAID' THEN ar.amount ELSE 0 END), 0) AS recovered_amount,
            a.amount - COALESCE(SUM(CASE WHEN s.status = 'PAID' THEN ar.amount ELSE 0 END), 0) AS outstanding_amount
        FROM driver_advances a
        LEFT JOIN salary_advance_recoveries ar ON ar.advance_id = a.id
        LEFT JOIN driver_salaries s ON s.id = ar.salary_id
        WHERE a.employment_id = %s
          AND a.status <> 'CANCELLED'
        GROUP BY a.id
        ORDER BY a.advance_date, a.id
    """


def list_outstanding_advances(employment_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(_outstanding_advances_query(), (employment_id,))
            return [row for row in cursor.fetchall() if row["outstanding_amount"] > 0]


def get_driver_money_detail(employment_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            employment = _load_employment(cursor, employment_id)
            cursor.execute(_outstanding_advances_query(), (employment_id,))
            advances = cursor.fetchall()
            cursor.execute(
                """
                SELECT
                    ds.id,
                    ds.salary_year,
                    ds.salary_month,
                    ds.base_salary,
                    ds.prorated_salary,
                    ds.advance_recovery,
                    ds.other_deductions,
                    ds.net_salary,
                    ds.status,
                    ds.payment_date,
                    ds.notes
                FROM driver_salaries ds
                WHERE ds.employment_id = %s
                ORDER BY ds.salary_year DESC, ds.salary_month DESC, ds.id DESC;
                """,
                (employment_id,),
            )
            salaries = cursor.fetchall()
            cursor.execute(
                """
                SELECT
                    ar.id,
                    ar.amount,
                    a.advance_date,
                    ds.salary_year,
                    ds.salary_month,
                    ds.status AS salary_status
                FROM salary_advance_recoveries ar
                JOIN driver_advances a ON a.id = ar.advance_id
                JOIN driver_salaries ds ON ds.id = ar.salary_id
                WHERE a.employment_id = %s
                ORDER BY ds.salary_year DESC, ds.salary_month DESC, ar.id DESC;
                """,
                (employment_id,),
            )
            recoveries = cursor.fetchall()
    return {
        "employment": employment,
        "advances": advances,
        "salaries": salaries,
        "recoveries": recoveries,
    }


def get_salary_preview(
    employment_id: int,
    salary_year: int,
    salary_month: int,
    other_deductions=0,
) -> dict:
    other_deductions = parse_non_negative_amount(other_deductions, "Other deductions")
    period_start, period_end = _month_bounds(salary_year, salary_month)
    days_in_month = Decimal(str(monthrange(int(salary_year), int(salary_month))[1]))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            employment = _load_employment(cursor, employment_id)
            worked_days = _overlap_days(period_start, period_end, employment)
            if worked_days <= 0:
                raise ValueError("This driver was not employed during that salary month.")
            monthly_salary = _get_effective_monthly_salary(cursor, employment, period_start)
            prorated_salary = _money(monthly_salary * Decimal(str(worked_days)) / days_in_month)
            cursor.execute(_outstanding_advances_query(), (employment_id,))
            outstanding_advances = [row for row in cursor.fetchall() if row["outstanding_amount"] > 0]

    available_for_recovery = max(prorated_salary - other_deductions, Decimal("0"))
    total_outstanding = sum((row["outstanding_amount"] for row in outstanding_advances), Decimal("0"))
    suggested_recovery = min(total_outstanding, available_for_recovery)
    return {
        "employment": employment,
        "period_start": period_start,
        "period_end": period_end,
        "worked_days": worked_days,
        "days_in_month": int(days_in_month),
        "base_salary": monthly_salary,
        "prorated_salary": prorated_salary,
        "other_deductions": other_deductions,
        "outstanding_advances": outstanding_advances,
        "total_outstanding_advances": total_outstanding,
        "suggested_recovery": suggested_recovery,
        "net_salary": prorated_salary - suggested_recovery - other_deductions,
    }


def _allocate_recovery(advances: list[dict], recovery_amount: Decimal) -> list[dict]:
    remaining = recovery_amount
    allocations = []
    for advance in advances:
        if remaining <= 0:
            break
        amount = min(advance["outstanding_amount"], remaining)
        if amount > 0:
            allocations.append({"advance_id": advance["id"], "amount": amount})
            remaining -= amount
    if remaining != 0:
        raise ValueError("Advance recovery could not be fully allocated.")
    return allocations


def _refresh_advance_status(cursor, advance_id: int) -> None:
    cursor.execute(
        """
        SELECT
            a.amount,
            COALESCE(SUM(CASE WHEN ds.status = 'PAID' THEN ar.amount ELSE 0 END), 0) AS recovered
        FROM driver_advances a
        LEFT JOIN salary_advance_recoveries ar ON ar.advance_id = a.id
        LEFT JOIN driver_salaries ds ON ds.id = ar.salary_id
        WHERE a.id = %s
        GROUP BY a.id;
        """,
        (advance_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return
    status = "REPAID" if row["recovered"] == row["amount"] else "ACTIVE"
    cursor.execute("UPDATE driver_advances SET status = %s WHERE id = %s;", (status, advance_id))


def record_driver_advance(
    employment_id: int,
    advance_date: date,
    amount,
    reason: str | None = None,
    notes: str | None = None,
    financial_account_id: int | None = None,
) -> dict:
    advance_date = _coerce_date(advance_date, "Advance date")
    amount = parse_positive_amount(amount, "Advance amount")
    account_id = financial_account_id or get_default_business_payment_account()["id"]
    limit = get_driver_advance_limit()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            employment = _load_employment(cursor, employment_id, lock=True)
            if employment["employment_status"] != "ACTIVE":
                raise ValueError("Advances can only be recorded for active employment.")
            if advance_date < employment["start_date"] or (
                employment["end_date"] and advance_date > employment["end_date"]
            ):
                raise ValueError("Advance date is outside this driver's employment period.")

            cursor.execute(_outstanding_advances_query(), (employment_id,))
            current_outstanding = sum(
                (row["outstanding_amount"] for row in cursor.fetchall() if row["outstanding_amount"] > 0),
                Decimal("0"),
            )
            if current_outstanding + amount > limit:
                raise ValueError(f"Outstanding advances cannot exceed K{limit:,.2f} for this driver.")

            cursor.execute(
                """
                SELECT id
                FROM financial_accounts
                WHERE id = %s
                  AND active = TRUE;
                """,
                (account_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Choose an active payment account.")

            description = f"Driver advance - {employment['driver_name']}"
            cursor.execute(
                """
                INSERT INTO financial_transactions (
                    account_id,
                    transaction_date,
                    transaction_type,
                    direction,
                    amount,
                    description,
                    notes
                )
                VALUES (%s, %s, 'DRIVER_ADVANCE', 'OUT', %s, %s, %s)
                RETURNING id;
                """,
                (account_id, advance_date, amount, description, clean_optional_text(notes)),
            )
            financial_transaction_id = cursor.fetchone()["id"]

            cursor.execute(
                """
                INSERT INTO driver_advances (
                    employment_id,
                    advance_date,
                    amount,
                    planned_repayment_amount,
                    financial_transaction_id,
                    status,
                    reason,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s, %s)
                RETURNING id, employment_id, advance_date, amount, status, financial_transaction_id;
                """,
                (
                    employment_id,
                    advance_date,
                    amount,
                    amount,
                    financial_transaction_id,
                    clean_optional_text(reason),
                    clean_optional_text(notes),
                ),
            )
            return cursor.fetchone()


def record_driver_salary(
    employment_id: int,
    salary_year: int,
    salary_month: int,
    payment_date: date,
    recovery_amount=None,
    other_deductions=0,
    notes: str | None = None,
    financial_account_id: int | None = None,
    existing_financial_transaction_id: int | None = None,
) -> dict:
    payment_date = _coerce_date(payment_date, "Payment date")
    preview = get_salary_preview(employment_id, salary_year, salary_month, other_deductions)
    recovery = preview["suggested_recovery"] if recovery_amount is None else parse_non_negative_amount(
        recovery_amount,
        "Advance recovery",
    )
    if recovery > preview["total_outstanding_advances"]:
        raise ValueError("Advance recovery cannot exceed outstanding advances.")
    if recovery + preview["other_deductions"] > preview["prorated_salary"]:
        raise ValueError("Salary deductions cannot make net salary negative.")
    net_salary = preview["prorated_salary"] - recovery - preview["other_deductions"]
    account_id = financial_account_id or get_default_business_payment_account()["id"]

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            employment = _load_employment(cursor, employment_id, lock=True)
            cursor.execute(_outstanding_advances_query(), (employment_id,))
            advances = [row for row in cursor.fetchall() if row["outstanding_amount"] > 0]
            allocations = _allocate_recovery(advances, recovery)

            financial_transaction_id = existing_financial_transaction_id
            if net_salary > 0:
                if existing_financial_transaction_id is None:
                    cursor.execute(
                        """
                        SELECT id
                        FROM financial_accounts
                        WHERE id = %s
                          AND active = TRUE;
                        """,
                        (account_id,),
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("Choose an active payment account.")
                    cursor.execute(
                        """
                        INSERT INTO financial_transactions (
                            account_id,
                            transaction_date,
                            transaction_type,
                            direction,
                            amount,
                            description,
                            notes
                        )
                        VALUES (%s, %s, 'DRIVER_SALARY', 'OUT', %s, %s, %s)
                        RETURNING id;
                        """,
                        (
                            account_id,
                            payment_date,
                            net_salary,
                            f"Driver salary - {employment['driver_name']}",
                            clean_optional_text(notes),
                        ),
                    )
                    financial_transaction_id = cursor.fetchone()["id"]
                else:
                    cursor.execute(
                        """
                        UPDATE financial_transactions
                        SET transaction_type = 'DRIVER_SALARY',
                            description = %s,
                            notes = COALESCE(%s, notes)
                        WHERE id = %s
                          AND direction = 'OUT'
                          AND amount = %s
                          AND transaction_date = %s
                        RETURNING id;
                        """,
                        (
                            f"Driver salary - {employment['driver_name']}",
                            clean_optional_text(notes),
                            existing_financial_transaction_id,
                            net_salary,
                            payment_date,
                        ),
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("Existing ledger payment does not match this salary.")
            elif existing_financial_transaction_id is not None:
                raise ValueError("A zero-net salary cannot be linked to an existing cash payment.")

            cursor.execute(
                """
                INSERT INTO driver_salaries (
                    employment_id,
                    salary_year,
                    salary_month,
                    base_salary,
                    prorated_salary,
                    advance_recovery,
                    other_deductions,
                    status,
                    payment_date,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'PAID', %s, %s, %s)
                RETURNING id, employment_id, salary_year, salary_month, prorated_salary,
                          advance_recovery, other_deductions, net_salary, status,
                          payment_date, financial_transaction_id;
                """,
                (
                    employment_id,
                    int(salary_year),
                    int(salary_month),
                    preview["base_salary"],
                    preview["prorated_salary"],
                    recovery,
                    preview["other_deductions"],
                    payment_date,
                    financial_transaction_id,
                    clean_optional_text(notes),
                ),
            )
            salary = cursor.fetchone()
            for allocation in allocations:
                cursor.execute(
                    """
                    INSERT INTO salary_advance_recoveries (salary_id, advance_id, amount)
                    VALUES (%s, %s, %s);
                    """,
                    (salary["id"], allocation["advance_id"], allocation["amount"]),
                )
                _refresh_advance_status(cursor, allocation["advance_id"])
            return salary


def cancel_driver_advance(advance_id: int, reason: str) -> dict:
    reason = clean_required_text(reason, "Correction reason")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.employment_id,
                    a.advance_date,
                    a.amount,
                    a.planned_repayment_amount,
                    a.status,
                    a.reason,
                    a.notes,
                    a.financial_transaction_id,
                    ft.account_id,
                    ft.transaction_date,
                    ft.transaction_type,
                    ft.direction,
                    ft.amount AS ledger_amount,
                    ft.description AS ledger_description,
                    ft.notes AS ledger_notes
                FROM driver_advances a
                JOIN financial_transactions ft ON ft.id = a.financial_transaction_id
                WHERE a.id = %s
                FOR UPDATE;
                """,
                (advance_id,),
            )
            advance = cursor.fetchone()
            if advance is None:
                raise ValueError("Advance record not found.")
            cursor.execute(
                """
                SELECT COUNT(*) AS recovery_count,
                       COALESCE(SUM(ar.amount), 0) AS recovered_amount
                FROM salary_advance_recoveries ar
                WHERE ar.advance_id = %s;
                """,
                (advance_id,),
            )
            recovery = cursor.fetchone()
            if recovery["recovery_count"] > 0:
                raise ValueError("This advance is already linked to salary recovery. Cancel the salary first.")

            audit = record_correction_audit(
                cursor,
                area="Driver Money",
                record_type="driver_advance",
                record_id=advance_id,
                action="CANCEL",
                reason=reason,
                snapshot={
                    "advance": dict(advance),
                    "recovery_count": recovery["recovery_count"],
                    "recovered_amount": recovery["recovered_amount"],
                },
            )
            cursor.execute("DELETE FROM driver_advances WHERE id = %s;", (advance_id,))
            cursor.execute("DELETE FROM financial_transactions WHERE id = %s;", (advance["financial_transaction_id"],))
            return audit


def cancel_driver_salary(salary_id: int, reason: str) -> dict:
    reason = clean_required_text(reason, "Correction reason")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM driver_salaries
                WHERE id = %s
                FOR UPDATE;
                """,
                (salary_id,),
            )
            salary = cursor.fetchone()
            if salary is None:
                raise ValueError("Salary record not found.")
            financial_transaction = None
            if salary["financial_transaction_id"] is not None:
                cursor.execute(
                    "SELECT * FROM financial_transactions WHERE id = %s;",
                    (salary["financial_transaction_id"],),
                )
                financial_transaction = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM salary_advance_recoveries WHERE salary_id = %s;",
                (salary_id,),
            )
            recoveries = cursor.fetchall()
            affected_advances = [row["advance_id"] for row in recoveries]
            cursor.execute(
                "SELECT * FROM salary_deduction_allocations WHERE salary_id = %s;",
                (salary_id,),
            )
            deductions = cursor.fetchall()
            audit = record_correction_audit(
                cursor,
                area="Driver Money",
                record_type="driver_salary",
                record_id=salary_id,
                action="CANCEL",
                reason=reason,
                snapshot={
                    "salary": dict(salary),
                    "financial_transaction": dict(financial_transaction) if financial_transaction else None,
                    "recoveries": [dict(row) for row in recoveries],
                    "deductions": [dict(row) for row in deductions],
                },
            )
            cursor.execute("DELETE FROM salary_advance_recoveries WHERE salary_id = %s;", (salary_id,))
            cursor.execute("DELETE FROM salary_deduction_allocations WHERE salary_id = %s;", (salary_id,))
            cursor.execute("DELETE FROM driver_salaries WHERE id = %s;", (salary_id,))
            if salary["financial_transaction_id"] is not None:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (salary["financial_transaction_id"],),
                )
            for advance_id in affected_advances:
                _refresh_advance_status(cursor, advance_id)
            return audit


def reclassify_expense_as_driver_salary(
    expense_id: int,
    employment_id: int,
    salary_year: int,
    salary_month: int,
    notes: str | None = None,
) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    e.id,
                    e.expense_date,
                    e.amount,
                    e.description,
                    e.financial_transaction_id,
                    ft.transaction_type,
                    ft.direction,
                    ft.amount AS ledger_amount,
                    ft.transaction_date
                FROM expenses e
                JOIN financial_transactions ft ON ft.id = e.financial_transaction_id
                WHERE e.id = %s
                FOR UPDATE;
                """,
                (expense_id,),
            )
            expense = cursor.fetchone()
            if expense is None:
                raise ValueError("Expense not found.")
            if expense["transaction_type"] != "EXPENSE" or expense["direction"] != "OUT":
                raise ValueError("This expense is not an ordinary outgoing expense.")
            if expense["amount"] != expense["ledger_amount"] or expense["expense_date"] != expense["transaction_date"]:
                raise ValueError("Expense and ledger row do not reconcile.")
            _load_employment(cursor, employment_id, lock=True)
            cursor.execute(
                """
                UPDATE financial_transactions
                SET transaction_type = 'DRIVER_SALARY',
                    description = %s,
                    notes = COALESCE(%s, notes)
                WHERE id = %s
                RETURNING id;
                """,
                (
                    "Driver salary - historical correction",
                    clean_optional_text(notes),
                    expense["financial_transaction_id"],
                ),
            )
            cursor.execute(
                """
                INSERT INTO driver_salaries (
                    employment_id,
                    salary_year,
                    salary_month,
                    base_salary,
                    prorated_salary,
                    advance_recovery,
                    other_deductions,
                    status,
                    payment_date,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, 0, 0, 'PAID', %s, %s, %s)
                RETURNING id, employment_id, salary_year, salary_month, prorated_salary,
                          advance_recovery, other_deductions, net_salary, status,
                          payment_date, financial_transaction_id;
                """,
                (
                    employment_id,
                    int(salary_year),
                    int(salary_month),
                    expense["amount"],
                    expense["amount"],
                    expense["expense_date"],
                    expense["financial_transaction_id"],
                    clean_optional_text(notes or f"Reclassified from expense {expense_id}: {expense['description']}"),
                ),
            )
            salary = cursor.fetchone()
            cursor.execute("DELETE FROM expense_allocations WHERE expense_id = %s;", (expense_id,))
            cursor.execute("DELETE FROM expenses WHERE id = %s;", (expense_id,))
            return salary
