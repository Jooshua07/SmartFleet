import importlib
from datetime import date, datetime

from psycopg.rows import dict_row

from database.connection import get_connection
import services.account_service as account_service
from utils.validation import clean_optional_text, clean_required_text, parse_positive_amount


RESTRICTED_EXPENSE_CATEGORIES = {
    "Driver Advances": "Driver advances are recoverable advances. Use the driver advance workflow instead.",
    "Driver Salaries": "Driver salaries must be recorded through the salary workflow so payroll is counted once.",
    "Loan Repayments": "Loan repayments are financing payments. Use the loan repayment workflow instead.",
    "Owner Drawings": "Owner drawings are not operating expenses. Use the owner drawing workflow instead.",
}


def is_restricted_expense_category(category_name: str | None) -> bool:
    return category_name in RESTRICTED_EXPENSE_CATEGORIES


def _clean_expense_title(value: str, existing_title: str | None = None) -> str:
    title = clean_required_text(value, "Expense title")
    if existing_title is not None and title == existing_title:
        return title
    if len(title) > 35:
        raise ValueError("Expense title must be 35 characters or fewer.")
    if len(title.split()) > 5:
        raise ValueError("Expense title must be five words or fewer.")
    return title


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


def get_operating_expense_categories() -> list[dict]:
    return [
        category
        for category in get_active_expense_categories()
        if not is_restricted_expense_category(category["name"])
    ]


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


def get_default_business_payment_account() -> dict:
    global account_service
    if not hasattr(account_service, "get_default_business_payment_account"):
        account_service = importlib.reload(account_service)
    return account_service.get_default_business_payment_account()


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


def _resolve_payment_account_id(financial_account_id: int | None) -> int:
    if financial_account_id is not None:
        return financial_account_id
    return get_default_business_payment_account()["id"]


def _load_expense_category(cursor, category_id: int) -> dict:
    cursor.execute(
        """
        SELECT id, name
        FROM expense_categories
        WHERE id = %s
          AND active = TRUE;
        """,
        (category_id,),
    )
    category = cursor.fetchone()
    if category is None:
        raise ValueError("Choose an active expense category.")
    if is_restricted_expense_category(category["name"]):
        raise ValueError(RESTRICTED_EXPENSE_CATEGORIES[category["name"]])
    return category


def record_business_expense(
    expense_date: date,
    category_id: int,
    amount,
    description: str,
    financial_account_id: int | None = None,
    scope: str = "GENERAL",
    bus_id: int | None = None,
    vendor_name: str | None = None,
    reference_number: str | None = None,
    notes: str | None = None,
) -> dict:
    expense_date = _coerce_expense_date(expense_date)
    amount = parse_positive_amount(amount, "Amount")
    description = _clean_expense_title(description)

    if scope not in {"GENERAL", "BUS"}:
        raise ValueError("Expense scope is not supported yet.")
    if scope == "BUS" and bus_id is None:
        raise ValueError("Choose a bus for a bus expense.")
    if scope == "GENERAL" and bus_id is not None:
        raise ValueError("General expenses cannot be linked to one bus.")
    financial_account_id = _resolve_payment_account_id(financial_account_id)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            _load_expense_category(cursor, category_id)

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
    financial_account_id: int | None = None,
    scope: str = "GENERAL",
    bus_id: int | None = None,
    vendor_name: str | None = None,
    reference_number: str | None = None,
    notes: str | None = None,
) -> dict:
    expense_date = _coerce_expense_date(expense_date)
    amount = parse_positive_amount(amount, "Amount")

    if scope not in {"GENERAL", "BUS"}:
        raise ValueError("Expense scope is not supported yet.")
    if scope == "BUS" and bus_id is None:
        raise ValueError("Choose a bus for a bus expense.")
    if scope == "GENERAL" and bus_id is not None:
        raise ValueError("General expenses cannot be linked to one bus.")
    financial_account_id = _resolve_payment_account_id(financial_account_id)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT e.financial_transaction_id, e.payment_source, e.description,
                       ec.name AS category_name, ft.transaction_type,
                       EXISTS(SELECT 1 FROM maintenance m WHERE m.expense_id=e.id) AS maintenance_linked
                FROM expenses e JOIN expense_categories ec ON ec.id=e.category_id
                LEFT JOIN financial_transactions ft ON ft.id=e.financial_transaction_id
                WHERE e.id = %s
                FOR UPDATE OF e;
                """,
                (expense_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Expense not found.")
            if existing["payment_source"] != "BUSINESS_ACCOUNT":
                raise ValueError("Only business-account expenses can be edited here.")
            if existing.get('maintenance_linked'):
                raise ValueError('Correct this payment in Record Servicing to keep maintenance history consistent.')
            if is_restricted_expense_category(existing.get('category_name')) or existing.get('transaction_type') not in (None,'EXPENSE','TRANSFER_FEE','OTHER'):
                raise ValueError('Use the loan, payroll or owner-money workflow to correct this specialized payment.')
            description = _clean_expense_title(description, existing["description"])

            _load_expense_category(cursor, category_id)

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
            result = cursor.fetchone()
            cursor.execute('DELETE FROM expense_allocations WHERE expense_id=%s', (expense_id,))
            return result


def delete_business_expense(expense_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT e.financial_transaction_id, e.payment_source, ec.name AS category_name, ft.transaction_type
                FROM expenses e JOIN expense_categories ec ON ec.id=e.category_id
                LEFT JOIN financial_transactions ft ON ft.id=e.financial_transaction_id
                WHERE e.id = %s
                FOR UPDATE OF e;
                """,
                (expense_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Expense not found.")
            if existing["payment_source"] != "BUSINESS_ACCOUNT":
                raise ValueError("Only business-account expenses can be deleted here.")
            if is_restricted_expense_category(existing.get('category_name')) or existing.get('transaction_type') not in (None,'EXPENSE','TRANSFER_FEE','OTHER'):
                raise ValueError('Use the specialized money workflow to correct this payment.')

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
