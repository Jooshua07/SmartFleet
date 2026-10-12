from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import parse_non_negative_amount


def get_accounts_for_management() -> list[dict]:
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
                GROUP BY fa.id
                ORDER BY fa.id;
                """
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


def get_negative_balance_warnings() -> list[str]:
    warnings = []
    for account in get_accounts_for_management():
        balance = account["calculated_balance"] or Decimal("0")
        if balance < 0:
            warnings.append(f"{account['name']} balance is below zero.")
    return warnings
