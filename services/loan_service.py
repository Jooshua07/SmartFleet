from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.account_service import get_default_business_payment_account
from services.correction_service import record_correction_audit
from utils.validation import (
    clean_optional_text,
    clean_required_text,
    parse_non_negative_amount,
    parse_optional_positive_int,
    parse_positive_amount,
)


def _coerce_date(value, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"{field_name} is required.")


def _owner_loan_id(cursor) -> int:
    cursor.execute(
        """
        SELECT id
        FROM owner_loans
        WHERE active = TRUE
        ORDER BY id
        LIMIT 1;
        """
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Owner loan account is not configured.")
    return row["id"]


def _category_id(cursor, name: str) -> int:
    cursor.execute("SELECT id FROM expense_categories WHERE name = %s;", (name,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Missing expense category: {name}")
    return row["id"]


def list_business_loans() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    bl.id,
                    bl.loan_name,
                    bl.lender,
                    bl.original_amount,
                    bl.start_date,
                    bl.term_months,
                    bl.default_monthly_repayment,
                    bl.status,
                    bl.notes,
                    COALESCE(SUM(lr.amount), 0) AS principal_repaid,
                    bl.original_amount - COALESCE(SUM(lr.amount), 0) AS outstanding_principal
                FROM business_loans bl
                LEFT JOIN loan_repayments lr ON lr.loan_id = bl.id
                GROUP BY bl.id
                ORDER BY
                    CASE bl.status WHEN 'ACTIVE' THEN 0 WHEN 'COMPLETED' THEN 1 ELSE 2 END,
                    bl.start_date DESC,
                    bl.id DESC;
                """
            )
            return cursor.fetchall()


def list_loan_repayments(limit: int = 30) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    lr.id,
                    lr.loan_id,
                    lr.repayment_date,
                    lr.amount,
                    lr.payment_source,
                    lr.financial_transaction_id,
                    lr.owner_loan_transaction_id,
                    lr.notes,
                    bl.loan_name,
                    bl.lender
                FROM loan_repayments lr
                LEFT JOIN business_loans bl ON bl.id = lr.loan_id
                ORDER BY lr.repayment_date DESC, lr.id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cursor.fetchall()


def list_owner_money_activity(limit: int = 30) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            owner_id = _owner_loan_id(cursor)
            cursor.execute(
                """
                (
                    SELECT
                        'OWNER_TRANSACTION' AS record_type,
                        olt.id AS record_id,
                        olt.transaction_date,
                        olt.transaction_type,
                        CASE
                            WHEN olt.transaction_type = 'OWNER_FUNDED'
                                 AND olt.financial_transaction_id IS NOT NULL
                                THEN 'Owner loan to business'
                            WHEN olt.transaction_type = 'OWNER_FUNDED'
                                THEN 'Owner funded payment'
                            WHEN olt.transaction_type = 'REPAYMENT'
                                THEN 'Business repaid owner'
                            ELSE olt.transaction_type
                        END AS label,
                        olt.amount,
                        olt.description,
                        olt.notes,
                        olt.expense_id,
                        olt.financial_transaction_id,
                        EXISTS (
                            SELECT 1
                            FROM loan_repayments lr
                            WHERE lr.owner_loan_transaction_id = olt.id
                        ) AS linked_to_loan_repayment
                    FROM owner_loan_transactions olt
                    WHERE olt.owner_loan_id = %s
                )
                UNION ALL
                (
                    SELECT
                        'OWNER_DRAWING' AS record_type,
                        e.id AS record_id,
                        e.expense_date AS transaction_date,
                        'OWNER_DRAWING' AS transaction_type,
                        'Owner drawing' AS label,
                        e.amount,
                        e.description,
                        e.notes,
                        e.id AS expense_id,
                        e.financial_transaction_id,
                        FALSE AS linked_to_loan_repayment
                    FROM expenses e
                    JOIN expense_categories ec ON ec.id = e.category_id
                    WHERE ec.name = 'Owner Drawings'
                )
                ORDER BY transaction_date DESC, record_id DESC
                LIMIT %s;
                """,
                (owner_id, limit),
            )
            return cursor.fetchall()


def get_owner_money_summary() -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            owner_id = _owner_loan_id(cursor)
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN transaction_type = 'OWNER_FUNDED' THEN amount ELSE 0 END), 0)
                        AS owner_funded,
                    COALESCE(SUM(CASE WHEN transaction_type = 'REPAYMENT' THEN amount ELSE 0 END), 0)
                        AS owner_repaid
                FROM owner_loan_transactions
                WHERE owner_loan_id = %s;
                """,
                (owner_id,),
            )
            summary = cursor.fetchone()
            cursor.execute(
                """
                SELECT
                    id,
                    transaction_date,
                    transaction_type,
                    amount,
                    description,
                    notes
                FROM owner_loan_transactions
                WHERE owner_loan_id = %s
                ORDER BY transaction_date DESC, id DESC
                LIMIT 20;
                """,
                (owner_id,),
            )
            transactions = cursor.fetchall()

    owner_funded = summary["owner_funded"] or Decimal("0")
    owner_repaid = summary["owner_repaid"] or Decimal("0")
    return {
        "owner_funded": owner_funded,
        "owner_repaid": owner_repaid,
        "owner_balance": owner_funded - owner_repaid,
        "transactions": transactions,
    }


def add_business_loan(
    loan_name: str,
    lender: str,
    original_amount,
    start_date: date,
    default_monthly_repayment=None,
    term_months=None,
    notes: str | None = None,
) -> dict:
    loan_name = clean_required_text(loan_name, "Loan name")
    lender = clean_required_text(lender, "Lender")
    original_amount = parse_positive_amount(original_amount, "Original principal")
    start_date = _coerce_date(start_date, "Start date")
    repayment = (
        None
        if default_monthly_repayment is None or str(default_monthly_repayment).strip() == ""
        else parse_positive_amount(default_monthly_repayment, "Known repayment amount")
    )
    term = parse_optional_positive_int(term_months, "Term")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO business_loans (
                    loan_name,
                    lender,
                    original_amount,
                    start_date,
                    term_months,
                    default_monthly_repayment,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, loan_name, lender, original_amount, start_date,
                          term_months, default_monthly_repayment, status, notes;
                """,
                (
                    loan_name,
                    lender,
                    original_amount,
                    start_date,
                    term,
                    repayment,
                    clean_optional_text(notes),
                ),
            )
            return cursor.fetchone()


def _loan_outstanding(cursor, loan_id: int | None) -> Decimal | None:
    if loan_id is None:
        return None
    cursor.execute(
        """
        SELECT original_amount
        FROM business_loans
        WHERE id = %s
        FOR UPDATE;
        """,
        (loan_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Choose a valid business loan.")
    cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS repaid
        FROM loan_repayments
        WHERE loan_id = %s;
        """,
        (loan_id,),
    )
    return row["original_amount"] - cursor.fetchone()["repaid"]


def _mark_loan_if_complete(cursor, loan_id: int | None) -> None:
    if loan_id is None:
        return
    cursor.execute(
        """
        UPDATE business_loans bl
        SET status = CASE
                WHEN bl.original_amount = COALESCE((
                    SELECT SUM(amount)
                    FROM loan_repayments
                    WHERE loan_id = bl.id
                ), 0)
                THEN 'COMPLETED'
                ELSE 'ACTIVE'
            END
        WHERE bl.id = %s;
        """,
        (loan_id,),
    )


def _owner_outstanding(cursor, owner_loan_id: int) -> Decimal:
    cursor.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN transaction_type = 'OWNER_FUNDED' THEN amount ELSE -amount END), 0)
            AS outstanding
        FROM owner_loan_transactions
        WHERE owner_loan_id = %s;
        """,
        (owner_loan_id,),
    )
    return cursor.fetchone()["outstanding"]


def cancel_loan_repayment(repayment_id: int, reason: str) -> dict:
    reason = clean_required_text(reason, "Correction reason")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM loan_repayments
                WHERE id = %s
                FOR UPDATE;
                """,
                (repayment_id,),
            )
            repayment = cursor.fetchone()
            if repayment is None:
                raise ValueError("Loan repayment not found.")

            financial_transaction = None
            owner_transaction = None
            if repayment["financial_transaction_id"] is not None:
                cursor.execute(
                    "SELECT * FROM financial_transactions WHERE id = %s;",
                    (repayment["financial_transaction_id"],),
                )
                financial_transaction = cursor.fetchone()
            if repayment["owner_loan_transaction_id"] is not None:
                cursor.execute(
                    "SELECT * FROM owner_loan_transactions WHERE id = %s FOR UPDATE;",
                    (repayment["owner_loan_transaction_id"],),
                )
                owner_transaction = cursor.fetchone()
                if owner_transaction is None:
                    raise ValueError("Linked owner transaction was not found.")
                outstanding = _owner_outstanding(cursor, owner_transaction["owner_loan_id"])
                if outstanding - owner_transaction["amount"] < 0:
                    raise ValueError(
                        "This owner-funded repayment cannot be reversed because later repayments depend on it."
                    )

            audit = record_correction_audit(
                cursor,
                area="Loans",
                record_type="loan_repayment",
                record_id=repayment_id,
                action="CANCEL",
                reason=reason,
                snapshot={
                    "loan_repayment": dict(repayment),
                    "financial_transaction": dict(financial_transaction) if financial_transaction else None,
                    "owner_loan_transaction": dict(owner_transaction) if owner_transaction else None,
                },
            )
            cursor.execute("DELETE FROM loan_repayments WHERE id = %s;", (repayment_id,))
            if repayment["financial_transaction_id"] is not None:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (repayment["financial_transaction_id"],),
                )
            if repayment["owner_loan_transaction_id"] is not None:
                cursor.execute(
                    "DELETE FROM owner_loan_transactions WHERE id = %s;",
                    (repayment["owner_loan_transaction_id"],),
                )
            _mark_loan_if_complete(cursor, repayment["loan_id"])
            return audit


def record_loan_repayment(
    repayment_date: date,
    principal_amount,
    payment_source: str,
    loan_id: int | None = None,
    financial_account_id: int | None = None,
    paid_to: str | None = None,
    interest_or_fees=0,
    reference: str | None = None,
    notes: str | None = None,
    existing_financial_transaction_id: int | None = None,
) -> dict:
    repayment_date = _coerce_date(repayment_date, "Repayment date")
    principal = parse_positive_amount(principal_amount, "Principal amount")
    fees = parse_non_negative_amount(interest_or_fees, "Interest or fees")
    if payment_source not in {"BUSINESS_ACCOUNT", "OWNER_PERSONAL"}:
        raise ValueError("Choose business funds or owner's personal funds.")
    if loan_id is None and not clean_optional_text(notes):
        raise ValueError("Unidentified loan repayment needs notes.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            outstanding = _loan_outstanding(cursor, loan_id)
            if outstanding is not None and principal > outstanding:
                raise ValueError("Principal repayment cannot exceed outstanding loan principal.")

            owner_tx_id = None
            financial_tx_id = existing_financial_transaction_id
            lender_label = clean_optional_text(paid_to)
            if loan_id is not None:
                cursor.execute("SELECT loan_name, lender FROM business_loans WHERE id = %s;", (loan_id,))
                loan = cursor.fetchone()
                lender_label = lender_label or loan["lender"]
            lender_label = lender_label or "unidentified lender"

            description = f"Loan repayment to {lender_label}"
            repayment_notes = "; ".join(
                value
                for value in [
                    clean_optional_text(reference),
                    clean_optional_text(notes),
                ]
                if value
            )

            if payment_source == "BUSINESS_ACCOUNT":
                account_id = financial_account_id or get_default_business_payment_account()["id"]
                if existing_financial_transaction_id is None:
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
                        VALUES (%s, %s, 'LOAN_REPAYMENT', 'OUT', %s, %s, %s)
                        RETURNING id;
                        """,
                        (account_id, repayment_date, principal, description, clean_optional_text(repayment_notes)),
                    )
                    financial_tx_id = cursor.fetchone()["id"]
                else:
                    cursor.execute(
                        """
                        UPDATE financial_transactions
                        SET transaction_type = 'LOAN_REPAYMENT',
                            description = %s,
                            notes = COALESCE(%s, notes)
                        WHERE id = %s
                          AND direction = 'OUT'
                          AND amount = %s
                          AND transaction_date = %s
                        RETURNING id;
                        """,
                        (
                            description,
                            clean_optional_text(repayment_notes),
                            existing_financial_transaction_id,
                            principal,
                            repayment_date,
                        ),
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("Existing ledger payment does not match this loan repayment.")

                if fees > 0:
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
                        VALUES (%s, %s, 'OTHER', 'OUT', %s, %s, %s);
                        """,
                        (
                            account_id,
                            repayment_date,
                            fees,
                            f"Loan finance charge to {lender_label}",
                            clean_optional_text(repayment_notes),
                        ),
                    )
            else:
                owner_id = _owner_loan_id(cursor)
                cursor.execute(
                    """
                    INSERT INTO owner_loan_transactions (
                        owner_loan_id,
                        transaction_date,
                        transaction_type,
                        amount,
                        description,
                        notes
                    )
                    VALUES (%s, %s, 'OWNER_FUNDED', %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        owner_id,
                        repayment_date,
                        principal,
                        f"Owner paid {lender_label} directly",
                        clean_optional_text(repayment_notes),
                    ),
                )
                owner_tx_id = cursor.fetchone()["id"]
                if fees > 0:
                    other_id = _category_id(cursor, "Other")
                    cursor.execute(
                        """
                        INSERT INTO expenses (
                            expense_date,
                            category_id,
                            amount,
                            description,
                            scope,
                            payment_source,
                            notes,
                            vendor_name,
                            reference_number
                        )
                        VALUES (%s, %s, %s, %s, 'GENERAL', 'OWNER_PERSONAL', %s, %s, %s)
                        RETURNING id;
                        """,
                        (
                            repayment_date,
                            other_id,
                            fees,
                            f"Loan finance charge - {lender_label}",
                            clean_optional_text(repayment_notes),
                            lender_label,
                            clean_optional_text(reference),
                        ),
                    )
                    expense_id = cursor.fetchone()["id"]
                    cursor.execute(
                        """
                        INSERT INTO owner_loan_transactions (
                            owner_loan_id,
                            transaction_date,
                            transaction_type,
                            amount,
                            description,
                            expense_id,
                            notes
                        )
                        VALUES (%s, %s, 'OWNER_FUNDED', %s, %s, %s, %s);
                        """,
                        (
                            owner_id,
                            repayment_date,
                            fees,
                            f"Owner paid loan finance charge to {lender_label}",
                            expense_id,
                            clean_optional_text(repayment_notes),
                        ),
                    )

            cursor.execute(
                """
                INSERT INTO loan_repayments (
                    loan_id,
                    repayment_date,
                    amount,
                    payment_source,
                    financial_transaction_id,
                    owner_loan_transaction_id,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, loan_id, repayment_date, amount, payment_source,
                          financial_transaction_id, owner_loan_transaction_id, notes;
                """,
                (
                    loan_id,
                    repayment_date,
                    principal,
                    payment_source,
                    financial_tx_id,
                    owner_tx_id,
                    clean_optional_text(f"{description}. {repayment_notes}".strip()),
                ),
            )
            repayment = cursor.fetchone()
            _mark_loan_if_complete(cursor, loan_id)
            return repayment


def record_unidentified_business_loan_repayment(
    repayment_date: date,
    amount,
    financial_account_id: int,
    paid_to: str,
    notes: str,
) -> dict:
    paid_to = clean_required_text(paid_to, "Paid to")
    notes = clean_required_text(notes, "Repayment notes")
    return record_loan_repayment(
        repayment_date=repayment_date,
        principal_amount=amount,
        payment_source="BUSINESS_ACCOUNT",
        loan_id=None,
        financial_account_id=financial_account_id,
        paid_to=paid_to,
        notes=notes,
    )


def record_owner_loan_to_business(
    transaction_date: date,
    amount,
    financial_account_id: int | None = None,
    notes: str | None = None,
) -> dict:
    transaction_date = _coerce_date(transaction_date, "Transaction date")
    amount = parse_positive_amount(amount, "Amount")
    account_id = financial_account_id or get_default_business_payment_account()["id"]
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            owner_id = _owner_loan_id(cursor)
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
                VALUES (%s, %s, 'OWNER_LOAN', 'IN', %s, 'Owner loan to business', %s)
                RETURNING id;
                """,
                (account_id, transaction_date, amount, clean_optional_text(notes)),
            )
            financial_transaction_id = cursor.fetchone()["id"]
            cursor.execute(
                """
                INSERT INTO owner_loan_transactions (
                    owner_loan_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    description,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, 'OWNER_FUNDED', %s, 'Owner loan to business', %s, %s)
                RETURNING id, transaction_date, amount, financial_transaction_id;
                """,
                (
                    owner_id,
                    transaction_date,
                    amount,
                    financial_transaction_id,
                    clean_optional_text(notes),
                ),
            )
            return cursor.fetchone()


def record_owner_drawing(
    transaction_date: date,
    amount,
    financial_account_id: int | None = None,
    notes: str | None = None,
    reference: str | None = None,
) -> dict:
    transaction_date = _coerce_date(transaction_date, "Transaction date")
    amount = parse_positive_amount(amount, "Amount")
    account_id = financial_account_id or get_default_business_payment_account()["id"]
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            category_id = _category_id(cursor, "Owner Drawings")
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
                VALUES (%s, %s, 'OWNER_DRAWING', 'OUT', %s, 'Owner drawing', %s)
                RETURNING id;
                """,
                (account_id, transaction_date, amount, clean_optional_text(notes)),
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
                    payment_source,
                    financial_account_id,
                    financial_transaction_id,
                    notes,
                    reference_number
                )
                VALUES (%s, %s, %s, 'Owner drawing', 'GENERAL', 'BUSINESS_ACCOUNT', %s, %s, %s, %s)
                RETURNING id, expense_date, amount, financial_transaction_id;
                """,
                (
                    transaction_date,
                    category_id,
                    amount,
                    account_id,
                    financial_transaction_id,
                    clean_optional_text(notes),
                    clean_optional_text(reference),
                ),
            )
            return cursor.fetchone()


def record_business_repayment_to_owner(
    transaction_date: date,
    amount,
    financial_account_id: int | None = None,
    notes: str | None = None,
) -> dict:
    transaction_date = _coerce_date(transaction_date, "Transaction date")
    amount = parse_positive_amount(amount, "Amount")
    account_id = financial_account_id or get_default_business_payment_account()["id"]
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            owner_id = _owner_loan_id(cursor)
            cursor.execute(
                "SELECT id FROM owner_loans WHERE id = %s FOR UPDATE;",
                (owner_id,),
            )
            cursor.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN transaction_type = 'OWNER_FUNDED' THEN amount ELSE -amount END), 0)
                    AS outstanding
                FROM owner_loan_transactions
                WHERE owner_loan_id = %s;
                """,
                (owner_id,),
            )
            outstanding = cursor.fetchone()["outstanding"]
            if amount > outstanding:
                raise ValueError("Owner repayment cannot exceed the amount owed to the owner.")
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
                VALUES (%s, %s, 'OWNER_LOAN_REPAYMENT', 'OUT', %s, 'Business repayment to owner', %s)
                RETURNING id;
                """,
                (account_id, transaction_date, amount, clean_optional_text(notes)),
            )
            financial_transaction_id = cursor.fetchone()["id"]
            cursor.execute(
                """
                INSERT INTO owner_loan_transactions (
                    owner_loan_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    description,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, 'REPAYMENT', %s, 'Business repayment to owner', %s, %s)
                RETURNING id, transaction_date, amount, financial_transaction_id;
                """,
                (
                    owner_id,
                    transaction_date,
                    amount,
                    financial_transaction_id,
                    clean_optional_text(notes),
                ),
            )
            return cursor.fetchone()


def cancel_owner_loan_transaction(owner_transaction_id: int, reason: str) -> dict:
    reason = clean_required_text(reason, "Correction reason")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM owner_loan_transactions
                WHERE id = %s
                FOR UPDATE;
                """,
                (owner_transaction_id,),
            )
            owner_transaction = cursor.fetchone()
            if owner_transaction is None:
                raise ValueError("Owner money transaction not found.")
            cursor.execute(
                """
                SELECT id
                FROM loan_repayments
                WHERE owner_loan_transaction_id = %s;
                """,
                (owner_transaction_id,),
            )
            if cursor.fetchone() is not None:
                raise ValueError("Reverse the linked loan repayment from the Loans page.")
            if owner_transaction["expense_id"] is not None:
                raise ValueError("This owner-funded expense needs a dedicated expense correction.")
            if owner_transaction["transaction_type"] == "OWNER_FUNDED":
                outstanding = _owner_outstanding(cursor, owner_transaction["owner_loan_id"])
                if outstanding - owner_transaction["amount"] < 0:
                    raise ValueError("This owner funding cannot be reversed because repayments depend on it.")

            financial_transaction = None
            if owner_transaction["financial_transaction_id"] is not None:
                cursor.execute(
                    "SELECT * FROM financial_transactions WHERE id = %s;",
                    (owner_transaction["financial_transaction_id"],),
                )
                financial_transaction = cursor.fetchone()

            audit = record_correction_audit(
                cursor,
                area="Owner Money",
                record_type="owner_loan_transaction",
                record_id=owner_transaction_id,
                action="CANCEL",
                reason=reason,
                snapshot={
                    "owner_loan_transaction": dict(owner_transaction),
                    "financial_transaction": dict(financial_transaction) if financial_transaction else None,
                },
            )
            cursor.execute("DELETE FROM owner_loan_transactions WHERE id = %s;", (owner_transaction_id,))
            if owner_transaction["financial_transaction_id"] is not None:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (owner_transaction["financial_transaction_id"],),
                )
            return audit


def cancel_owner_drawing(expense_id: int, reason: str) -> dict:
    reason = clean_required_text(reason, "Correction reason")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    e.*,
                    ec.name AS category_name
                FROM expenses e
                JOIN expense_categories ec ON ec.id = e.category_id
                WHERE e.id = %s
                  AND ec.name = 'Owner Drawings'
                FOR UPDATE OF e;
                """,
                (expense_id,),
            )
            drawing = cursor.fetchone()
            if drawing is None:
                raise ValueError("Owner drawing not found.")
            financial_transaction = None
            if drawing["financial_transaction_id"] is not None:
                cursor.execute(
                    "SELECT * FROM financial_transactions WHERE id = %s;",
                    (drawing["financial_transaction_id"],),
                )
                financial_transaction = cursor.fetchone()

            audit = record_correction_audit(
                cursor,
                area="Owner Money",
                record_type="owner_drawing",
                record_id=expense_id,
                action="CANCEL",
                reason=reason,
                snapshot={
                    "expense": dict(drawing),
                    "financial_transaction": dict(financial_transaction) if financial_transaction else None,
                },
            )
            cursor.execute("DELETE FROM expense_allocations WHERE expense_id = %s;", (expense_id,))
            cursor.execute("DELETE FROM expenses WHERE id = %s;", (expense_id,))
            if drawing["financial_transaction_id"] is not None:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (drawing["financial_transaction_id"],),
                )
            return audit


def associate_loan_repayment(repayment_id: int, loan_id: int) -> dict:
    """Associate an unidentified principal payment without creating another cash movement."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM loan_repayments WHERE id=%s FOR UPDATE", (repayment_id,))
            repayment = cursor.fetchone()
            if repayment is None or repayment["loan_id"] is not None:
                raise ValueError("Choose an unidentified repayment.")
            outstanding = _loan_outstanding(cursor, loan_id)
            if repayment["amount"] > outstanding:
                raise ValueError("Principal repayment cannot exceed outstanding loan principal.")
            cursor.execute("UPDATE loan_repayments SET loan_id=%s WHERE id=%s RETURNING *", (loan_id, repayment_id))
            result = cursor.fetchone()
            _mark_loan_if_complete(cursor, loan_id)
            return result


def reclassify_expense_as_loan_repayment(
    expense_id: int,
    loan_id: int | None = None,
    paid_to: str | None = None,
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
                    e.vendor_name,
                    e.notes,
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
            outstanding = _loan_outstanding(cursor, loan_id)
            if outstanding is not None and expense["amount"] > outstanding:
                raise ValueError("Principal repayment cannot exceed outstanding loan principal.")
            lender_label = clean_optional_text(paid_to or expense["vendor_name"]) or "unidentified lender"
            repayment_notes = notes or f"Reclassified from expense {expense_id}: {expense['description']}. {expense['notes'] or ''}"
            cursor.execute(
                """
                UPDATE financial_transactions
                SET transaction_type = 'LOAN_REPAYMENT',
                    description = %s,
                    notes = COALESCE(%s, notes)
                WHERE id = %s
                RETURNING id;
                """,
                (
                    f"Loan repayment to {lender_label}",
                    clean_optional_text(repayment_notes),
                    expense["financial_transaction_id"],
                ),
            )
            cursor.execute(
                """
                INSERT INTO loan_repayments (
                    loan_id,
                    repayment_date,
                    amount,
                    payment_source,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, %s, 'BUSINESS_ACCOUNT', %s, %s)
                RETURNING id, loan_id, repayment_date, amount, payment_source,
                          financial_transaction_id, owner_loan_transaction_id, notes;
                """,
                (
                    loan_id,
                    expense["expense_date"],
                    expense["amount"],
                    expense["financial_transaction_id"],
                    clean_optional_text(f"Loan repayment to {lender_label}. {repayment_notes}"),
                ),
            )
            repayment = cursor.fetchone()
            cursor.execute("DELETE FROM expense_allocations WHERE expense_id = %s;", (expense_id,))
            cursor.execute("DELETE FROM expenses WHERE id = %s;", (expense_id,))
            _mark_loan_if_complete(cursor, loan_id)
            return repayment
