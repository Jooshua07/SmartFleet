from psycopg.rows import dict_row

from database.connection import get_connection
from services.preset_service import get_default_collection_account_type
from utils.validation import parse_non_negative_amount


def get_accounts_for_management(on_date=None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    fa.id,
                    fa.name,
                    fa.account_type,
                    fa.opening_balance,
                    fa.active,
                    fa.notes,
                    fa.opening_balance
                        + COALESCE(SUM(
                            CASE
                                WHEN ft.direction = 'IN' THEN ft.amount
                                WHEN ft.direction = 'OUT' THEN -ft.amount
                                ELSE 0
                            END
                        ), 0) AS calculated_balance,
                    COUNT(ft.id) AS transaction_count
                FROM financial_accounts fa
                LEFT JOIN financial_transactions ft ON ft.account_id = fa.id
                    AND (%s::date IS NULL OR ft.transaction_date <= %s)
                GROUP BY fa.id
                ORDER BY fa.id;
                """,
                (on_date, on_date),
            )
            return cursor.fetchall()


def update_opening_balance(account_id: int, opening_balance) -> dict:
    amount = parse_non_negative_amount(opening_balance, "Opening balance")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE financial_accounts
                SET opening_balance = %s
                WHERE id = %s
                RETURNING id, name, opening_balance;
                """,
                (amount, account_id),
            )
            account = cursor.fetchone()
            if account is None:
                raise ValueError("Account not found.")
            return account


def get_default_business_payment_account() -> dict:
    account_type = get_default_collection_account_type()
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, name, account_type
                FROM financial_accounts
                WHERE active = TRUE
                  AND account_type = %s
                ORDER BY id
                LIMIT 1;
                """,
                (account_type,),
            )
            account = cursor.fetchone()
            if account is None:
                raise ValueError(f"No active {account_type.replace('_', ' ').title()} account is configured.")
            return account


def get_negative_balance_warnings() -> list[str]:
    return []
