from datetime import date, datetime

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import clean_optional_text, clean_required_text, parse_positive_amount


def get_active_expense_categories() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name
                FROM expense_categories
                WHERE active = TRUE
                ORDER BY name;
                """
            )
            return cursor.fetchall()


def get_active_payment_accounts() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, account_type
                FROM financial_accounts
                WHERE active = TRUE
                ORDER BY id;
                """
            )
            return cursor.fetchall()


def get_recent_expenses(limit: int = 10) -> list[dict]:
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
                    e.vendor_name,
                    e.reference_number,
                    e.scope,
                    e.payment_source,
                    fa.name AS account_name,
                    b.registration_number
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN financial_accounts fa ON fa.id = e.financial_account_id
                LEFT JOIN buses b ON b.id = e.bus_id
                ORDER BY e.expense_date DESC, e.id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cursor.fetchall()


def get_expense(expense_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    e.id,
                    e.expense_date,
                    e.category_id,
                    ec.name AS category_name,
                    e.amount,
                    e.description,
                    e.vendor_name,
                    e.reference_number,
                    e.scope,
                    e.bus_id,
                    e.payment_source,
                    e.financial_account_id,
                    e.financial_transaction_id,
                    e.notes,
                    b.registration_number
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                LEFT JOIN buses b ON b.id = e.bus_id
                WHERE e.id = %s;
                """,
                (expense_id,),
            )
            expense = cursor.fetchone()
            if expense is None:
                raise ValueError("Expense not found.")
            return expense


def _coerce_expense_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError("Expense date is required.")


def record_business_expense(
    expense_date: date,
    category_id: int,
    amount,
    description: str,
    financial_account_id: int,
    scope: str = "GENERAL",
    bus_id: int | None = None,
    vendor_name: str | None = None,
    reference_number: str | None = None,
    notes: str | None = None,
) -> dict:
    expense_date = _coerce_expense_date(expense_date)
    amount = parse_positive_amount(amount, "Amount")
    description = clean_required_text(description, "Description")

    if scope not in {"GENERAL", "BUS"}:
        raise ValueError("Expense scope is not supported yet.")
    if scope == "BUS" and bus_id is None:
        raise ValueError("Choose a bus for a bus expense.")
    if scope == "GENERAL" and bus_id is not None:
        raise ValueError("General expenses cannot be linked to one bus.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id
                FROM expense_categories
                WHERE id = %s
                  AND active = TRUE;
                """,
                (category_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Choose an active expense category.")

            cursor.execute(
                """
                SELECT id
                FROM financial_accounts
                WHERE id = %s
                  AND active = TRUE;
                """,
                (financial_account_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Choose an active payment account.")

            if bus_id is not None:
                cursor.execute(
                    """
                    SELECT id
                    FROM buses
                    WHERE id = %s;
                    """,
                    (bus_id,),
                )
                if cursor.fetchone() is None:
                    raise ValueError("Choose a valid bus.")

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
                VALUES (%s, %s, 'EXPENSE', 'OUT', %s, %s, %s)
                RETURNING id;
                """,
                (
                    financial_account_id,
                    expense_date,
                    amount,
                    description,
                    clean_optional_text(notes),
                ),
            )
            financial_transaction_id = cursor.fetchone()["id"]

            cursor.execute(
                """
                INSERT INTO expenses (
                    expense_date,
                    category_id,
                    amount,
                    description,
                    scope,
                    bus_id,
                    payment_source,
                    financial_account_id,
                    financial_transaction_id,
                    notes,
                    vendor_name,
                    reference_number
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'BUSINESS_ACCOUNT', %s, %s, %s, %s, %s)
                RETURNING id, expense_date, amount, description;
                """,
                (
                    expense_date,
                    category_id,
                    amount,
                    description,
                    scope,
                    bus_id,
                    financial_account_id,
                    financial_transaction_id,
                    clean_optional_text(notes),
                    clean_optional_text(vendor_name),
                    clean_optional_text(reference_number),
                ),
            )
            return cursor.fetchone()


def update_business_expense(
    expense_id: int,
    expense_date: date,
    category_id: int,
    amount,
    description: str,
    financial_account_id: int,
    scope: str = "GENERAL",
    bus_id: int | None = None,
    vendor_name: str | None = None,
    reference_number: str | None = None,
    notes: str | None = None,
) -> dict:
    expense_date = _coerce_expense_date(expense_date)
    amount = parse_positive_amount(amount, "Amount")
    description = clean_required_text(description, "Description")

    if scope not in {"GENERAL", "BUS"}:
        raise ValueError("Expense scope is not supported yet.")
    if scope == "BUS" and bus_id is None:
        raise ValueError("Choose a bus for a bus expense.")
    if scope == "GENERAL" and bus_id is not None:
        raise ValueError("General expenses cannot be linked to one bus.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT financial_transaction_id, payment_source
                FROM expenses
                WHERE id = %s
                FOR UPDATE;
                """,
                (expense_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Expense not found.")
            if existing["payment_source"] != "BUSINESS_ACCOUNT":
                raise ValueError("Only business-account expenses can be edited here.")

            cursor.execute(
                """
                SELECT id
                FROM expense_categories
                WHERE id = %s
                  AND active = TRUE;
                """,
                (category_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Choose an active expense category.")

            cursor.execute(
                """
                SELECT id
                FROM financial_accounts
                WHERE id = %s
                  AND active = TRUE;
                """,
                (financial_account_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Choose an active payment account.")

            if bus_id is not None:
                cursor.execute("SELECT id FROM buses WHERE id = %s;", (bus_id,))
                if cursor.fetchone() is None:
                    raise ValueError("Choose a valid bus.")

            cursor.execute(
                """
                UPDATE financial_transactions
                SET
                    account_id = %s,
                    transaction_date = %s,
                    amount = %s,
                    description = %s,
                    notes = %s
                WHERE id = %s
                RETURNING id;
                """,
                (
                    financial_account_id,
                    expense_date,
                    amount,
                    description,
                    clean_optional_text(notes),
                    existing["financial_transaction_id"],
                ),
            )
            if cursor.fetchone() is None:
                raise ValueError("Linked ledger entry not found.")

            cursor.execute(
                """
                UPDATE expenses
                SET
                    expense_date = %s,
                    category_id = %s,
                    amount = %s,
                    description = %s,
                    scope = %s,
                    bus_id = %s,
                    financial_account_id = %s,
                    vendor_name = %s,
                    reference_number = %s,
                    notes = %s
                WHERE id = %s
                RETURNING id, expense_date, amount, description;
                """,
                (
                    expense_date,
                    category_id,
                    amount,
                    description,
                    scope,
                    bus_id,
                    financial_account_id,
                    clean_optional_text(vendor_name),
                    clean_optional_text(reference_number),
                    clean_optional_text(notes),
                    expense_id,
                ),
            )
            return cursor.fetchone()


def delete_business_expense(expense_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT financial_transaction_id, payment_source
                FROM expenses
                WHERE id = %s
                FOR UPDATE;
                """,
                (expense_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Expense not found.")
            if existing["payment_source"] != "BUSINESS_ACCOUNT":
                raise ValueError("Only business-account expenses can be deleted here.")

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM maintenance
                WHERE expense_id = %s;
                """,
                (expense_id,),
            )
            if cursor.fetchone()["count"] > 0:
                raise ValueError("This expense is linked to maintenance and cannot be deleted here.")

            cursor.execute("DELETE FROM expense_allocations WHERE expense_id = %s;", (expense_id,))
            cursor.execute("DELETE FROM expenses WHERE id = %s;", (expense_id,))
            cursor.execute(
                "DELETE FROM financial_transactions WHERE id = %s;",
                (existing["financial_transaction_id"],),
            )
