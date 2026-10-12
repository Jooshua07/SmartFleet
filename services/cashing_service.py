from datetime import date, datetime
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from services.preset_service import (
    get_default_collection_account_type,
    get_effective_cashing_rates,
)
from utils.validation import clean_optional_text, parse_non_negative_amount


def get_active_financial_accounts() -> list[dict]:
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


def get_collection_destination_account() -> dict:
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


def get_cashing_rates_for_date(on_date: date) -> dict[str, Decimal]:
    rates = get_effective_cashing_rates(on_date)
    missing = {"NORMAL_DAY", "SUNDAY"} - set(rates)
    if missing:
        raise ValueError("Cashing rates are not fully configured.")
    return rates


def get_recent_cashing_collections(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.collection_date,
                    c.total_amount,
                    c.financial_account_id,
                    c.notes,
                    fa.name AS account_name,
                    COUNT(r.id) AS bus_count
                FROM remittance_collections c
                JOIN financial_accounts fa ON fa.id = c.financial_account_id
                LEFT JOIN remittances r ON r.collection_id = c.id
                GROUP BY c.id, fa.name
                ORDER BY c.collection_date DESC, c.id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cursor.fetchall()


def get_cashing_collection(collection_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.collection_date,
                    c.financial_account_id,
                    c.financial_transaction_id,
                    c.total_amount,
                    c.notes,
                    fa.name AS account_name
                FROM remittance_collections c
                JOIN financial_accounts fa ON fa.id = c.financial_account_id
                WHERE c.id = %s;
                """,
                (collection_id,),
            )
            collection = cursor.fetchone()
            if collection is None:
                raise ValueError("Cashing collection not found.")

            cursor.execute(
                """
                SELECT
                    r.id,
                    r.bus_id,
                    b.registration_number,
                    r.normal_days,
                    r.sunday_days,
                    r.actual_amount,
                    r.expected_amount,
                    r.variance,
                    r.explanation,
                    r.notes
                FROM remittances r
                JOIN buses b ON b.id = r.bus_id
                WHERE r.collection_id = %s
                ORDER BY b.registration_number;
                """,
                (collection_id,),
            )
            return {"collection": collection, "entries": cursor.fetchall()}


def _format_duplicate(existing_entries: list[dict]) -> str:
    first_entries = existing_entries[:3]
    examples = ", ".join(
        f"{entry['registration_number']} on {entry['collection_date']:%d/%m/%Y}"
        for entry in first_entries
    )
    if len(existing_entries) > 3:
        examples = f"{examples}, and {len(existing_entries) - 3} more"
    return f"Cashing already exists for {examples}."


def _find_existing_cashing_entries(
    cursor,
    collection_date: date,
    bus_ids: list[int],
    exclude_collection_id: int | None = None,
) -> list[dict]:
    if not bus_ids:
        return []

    excluded_clause = ""
    params: list = [collection_date, bus_ids]
    if exclude_collection_id is not None:
        excluded_clause = "AND c.id <> %s"
        params.append(exclude_collection_id)

    cursor.execute(
        f"""
        SELECT
            c.collection_date,
            r.bus_id,
            b.registration_number
        FROM remittance_collections c
        JOIN remittances r ON r.collection_id = c.id
        JOIN buses b ON b.id = r.bus_id
        WHERE c.collection_date = %s
          AND r.bus_id = ANY(%s)
          {excluded_clause}
        ORDER BY c.collection_date, b.registration_number;
        """,
        params,
    )
    return cursor.fetchall()


def _coerce_collection_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError("Collection date is required.")


def _clean_direct_entry(entry: dict) -> dict:
    normal_amount = parse_non_negative_amount(
        entry.get("normal_amount", entry.get("actual_amount", 0)),
        "Amount",
    )
    sunday_amount = parse_non_negative_amount(entry.get("sunday_amount", 0), "Sunday amount")
    actual_amount = normal_amount + sunday_amount
    if actual_amount <= 0:
        raise ValueError("Enter an amount for each selected bus.")

    return {
        "bus_id": entry["bus_id"],
        "normal_days": 1 if normal_amount > 0 else 0,
        "normal_daily_rate": normal_amount if normal_amount > 0 else Decimal("0.00"),
        "sunday_days": 1 if sunday_amount > 0 else 0,
        "sunday_rate": sunday_amount if sunday_amount > 0 else Decimal("0.00"),
        "actual_amount": actual_amount,
        "explanation": clean_optional_text(entry.get("explanation")),
        "notes": clean_optional_text(entry.get("notes")),
    }


def _clean_direct_entries(entries: list[dict]) -> list[dict]:
    cleaned_entries = [_clean_direct_entry(entry) for entry in entries if entry.get("include")]
    if not cleaned_entries:
        raise ValueError("Choose at least one bus.")
    return cleaned_entries


def _assert_active_account(cursor, financial_account_id: int) -> None:
    account_type = get_default_collection_account_type()
    cursor.execute(
        """
        SELECT id, account_type
        FROM financial_accounts
        WHERE id = %s
          AND active = TRUE;
        """,
        (financial_account_id,),
    )
    account = cursor.fetchone()
    if account is None:
        raise ValueError("Choose an active account.")
    if account["account_type"] != account_type:
        raise ValueError("Cashing must be paid into Airtel Money.")


def _insert_financial_transaction(
    cursor,
    financial_account_id: int,
    collection_date: date,
    total_amount: Decimal,
    notes: str | None,
) -> int:
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
        VALUES (%s, %s, 'CASHING', 'IN', %s, %s, %s)
        RETURNING id;
        """,
        (
            financial_account_id,
            collection_date,
            total_amount,
            "Cashing collection",
            clean_optional_text(notes),
        ),
    )
    return cursor.fetchone()["id"]


def _update_financial_transaction(
    cursor,
    transaction_id: int,
    financial_account_id: int,
    collection_date: date,
    total_amount: Decimal,
    notes: str | None,
) -> None:
    cursor.execute(
        """
        UPDATE financial_transactions
        SET
            account_id = %s,
            transaction_date = %s,
            amount = %s,
            description = %s,
            notes = %s
        WHERE id = %s;
        """,
        (
            financial_account_id,
            collection_date,
            total_amount,
            "Cashing collection",
            clean_optional_text(notes),
            transaction_id,
        ),
    )


def _insert_remittance_rows(cursor, collection_id: int, cleaned_entries: list[dict]) -> None:
    for entry in cleaned_entries:
        cursor.execute(
            """
            INSERT INTO remittances (
                collection_id,
                bus_id,
                normal_days,
                normal_daily_rate,
                sunday_days,
                sunday_rate,
                actual_amount,
                explanation,
                notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                collection_id,
                entry["bus_id"],
                entry["normal_days"],
                entry["normal_daily_rate"],
                entry["sunday_days"],
                entry["sunday_rate"],
                entry["actual_amount"],
                entry["explanation"],
                entry["notes"],
            ),
        )


def record_direct_cashing_collection(
    collection_date: date,
    financial_account_id: int,
    entries: list[dict],
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_collection_date(collection_date)
    cleaned_entries = _clean_direct_entries(entries)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            _assert_active_account(cursor, financial_account_id)
            existing_entries = _find_existing_cashing_entries(
                cursor,
                collection_date,
                [entry["bus_id"] for entry in cleaned_entries],
            )
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            total_amount = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))
            financial_transaction_id = _insert_financial_transaction(
                cursor,
                financial_account_id,
                collection_date,
                total_amount,
                notes,
            )
            cursor.execute(
                """
                INSERT INTO remittance_collections (
                    collection_date,
                    financial_account_id,
                    total_amount,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, collection_date, total_amount;
                """,
                (
                    collection_date,
                    financial_account_id,
                    total_amount,
                    financial_transaction_id,
                    clean_optional_text(notes),
                ),
            )
            collection = cursor.fetchone()
            _insert_remittance_rows(cursor, collection["id"], cleaned_entries)
            return collection


def update_direct_cashing_collection(
    collection_id: int,
    collection_date: date,
    financial_account_id: int,
    entries: list[dict],
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_collection_date(collection_date)
    cleaned_entries = _clean_direct_entries(entries)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT financial_transaction_id
                FROM remittance_collections
                WHERE id = %s
                FOR UPDATE;
                """,
                (collection_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Cashing collection not found.")

            _assert_active_account(cursor, financial_account_id)
            existing_entries = _find_existing_cashing_entries(
                cursor,
                collection_date,
                [entry["bus_id"] for entry in cleaned_entries],
                exclude_collection_id=collection_id,
            )
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            total_amount = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))
            financial_transaction_id = existing["financial_transaction_id"]
            if financial_transaction_id is None:
                financial_transaction_id = _insert_financial_transaction(
                    cursor,
                    financial_account_id,
                    collection_date,
                    total_amount,
                    notes,
                )
            else:
                _update_financial_transaction(
                    cursor,
                    financial_transaction_id,
                    financial_account_id,
                    collection_date,
                    total_amount,
                    notes,
                )

            cursor.execute("DELETE FROM remittances WHERE collection_id = %s;", (collection_id,))
            cursor.execute(
                """
                UPDATE remittance_collections
                SET
                    collection_date = %s,
                    financial_account_id = %s,
                    total_amount = %s,
                    financial_transaction_id = %s,
                    notes = %s
                WHERE id = %s
                RETURNING id, collection_date, total_amount;
                """,
                (
                    collection_date,
                    financial_account_id,
                    total_amount,
                    financial_transaction_id,
                    clean_optional_text(notes),
                    collection_id,
                ),
            )
            collection = cursor.fetchone()
            _insert_remittance_rows(cursor, collection_id, cleaned_entries)
            return collection


def delete_cashing_collection(collection_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT financial_transaction_id
                FROM remittance_collections
                WHERE id = %s
                FOR UPDATE;
                """,
                (collection_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Cashing collection not found.")

            cursor.execute("DELETE FROM remittances WHERE collection_id = %s;", (collection_id,))
            cursor.execute("DELETE FROM remittance_collections WHERE id = %s;", (collection_id,))
            if existing["financial_transaction_id"] is not None:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (existing["financial_transaction_id"],),
                )
