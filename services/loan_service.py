from datetime import date, datetime

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import clean_optional_text, clean_required_text, parse_positive_amount


def _coerce_repayment_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError("Repayment date is required.")


def record_unidentified_business_loan_repayment(
    repayment_date: date,
    amount,
    financial_account_id: int,
    paid_to: str,
    notes: str,
) -> dict:
    repayment_date = _coerce_repayment_date(repayment_date)
    amount = parse_positive_amount(amount, "Repayment amount")
    paid_to = clean_required_text(paid_to, "Paid to")
    notes = clean_required_text(notes, "Repayment notes")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
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

            description = f"Loan repayment to {paid_to}"
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
                (
                    financial_account_id,
                    repayment_date,
                    amount,
                    description,
                    clean_optional_text(notes),
                ),
            )
            financial_transaction_id = cursor.fetchone()["id"]

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
                VALUES (NULL, %s, %s, 'BUSINESS_ACCOUNT', %s, %s)
                RETURNING id, repayment_date, amount, payment_source, financial_transaction_id, notes;
                """,
                (
                    repayment_date,
                    amount,
                    financial_transaction_id,
                    f"{description}. {notes}",
                ),
            )
            return cursor.fetchone()

