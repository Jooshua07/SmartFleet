from datetime import date, datetime
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import clean_optional_text, parse_non_negative_amount


def _get_active_cashing_rates(cursor, on_date: date) -> dict[str, Decimal]:
    cursor.execute(
        """
        SELECT rate_type, amount
        FROM cashing_rates
        WHERE active = TRUE
          AND (effective_to IS NULL OR effective_to >= %s);
        """,
        (on_date,),
    )
    rows = cursor.fetchall()
    rates = {row["rate_type"]: row["amount"] for row in rows}
    missing = {"NORMAL_DAY", "SUNDAY"} - set(rates)
    if missing:
        raise ValueError("Cashing rates are not fully configured.")
    return rates


def get_active_cashing_rates(on_date: date) -> dict[str, Decimal]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            return _get_active_cashing_rates(cursor, on_date)


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
    collection_dates: list[date],
    bus_ids: list[int],
) -> list[dict]:
    if not collection_dates or not bus_ids:
        return []

    cursor.execute(
        """
        SELECT
            c.collection_date,
            r.bus_id,
            b.registration_number
        FROM remittance_collections c
        JOIN remittances r ON r.collection_id = c.id
        JOIN buses b ON b.id = r.bus_id
        WHERE c.collection_date = ANY(%s)
          AND r.bus_id = ANY(%s)
        ORDER BY c.collection_date, b.registration_number;
        """,
        (collection_dates, bus_ids),
    )
    return cursor.fetchall()


def _clean_entry(entry: dict, rates: dict[str, Decimal]) -> dict:
    actual_amount = parse_non_negative_amount(entry.get("actual_amount", 0), "Actual amount")
    normal_days = int(entry.get("normal_days") or 0)
    sunday_days = int(entry.get("sunday_days") or 0)
    if normal_days < 0 or sunday_days < 0:
        raise ValueError("Cashing days cannot be negative.")

    expected_amount = (
        Decimal(normal_days) * rates["NORMAL_DAY"]
        + Decimal(sunday_days) * rates["SUNDAY"]
    )
    explanation = clean_optional_text(entry.get("explanation"))
    if actual_amount != expected_amount and not explanation:
        raise ValueError("Add a reason when actual cashing differs from expected cashing.")

    return {
        "bus_id": entry["bus_id"],
        "normal_days": normal_days,
        "sunday_days": sunday_days,
        "actual_amount": actual_amount,
        "expected_amount": expected_amount,
        "explanation": explanation,
        "notes": clean_optional_text(entry.get("notes")),
    }


def _clean_direct_entry(entry: dict) -> dict:
    normal_amount = parse_non_negative_amount(entry.get("normal_amount", entry.get("actual_amount", 0)), "Amount")
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
        "expected_amount": actual_amount,
        "explanation": clean_optional_text(entry.get("explanation")),
        "notes": clean_optional_text(entry.get("notes")),
    }


def _coerce_collection_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError("Collection date is required.")


def _record_cashing_collection_with_cursor(
    cursor,
    collection_date: date,
    financial_account_id: int,
    cleaned_entries: list[dict],
    notes: str | None = None,
) -> dict:
    total_amount = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))

    financial_transaction_id = None
    if total_amount > 0:
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
        financial_transaction_id = cursor.fetchone()["id"]

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
                collection["id"],
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

    return collection


def _assert_active_account(cursor, financial_account_id: int) -> None:
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
        raise ValueError("Choose an active account.")


def record_cashing_collection(
    collection_date: date,
    financial_account_id: int,
    entries: list[dict],
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_collection_date(collection_date)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            rates = _get_active_cashing_rates(cursor, collection_date)
            cleaned_entries = []
            for entry in entries:
                if entry.get("include"):
                    cleaned = _clean_entry(entry, rates)
                    cleaned["normal_daily_rate"] = rates["NORMAL_DAY"]
                    cleaned["sunday_rate"] = rates["SUNDAY"]
                    cleaned_entries.append(cleaned)

            if not cleaned_entries:
                raise ValueError("Select at least one bus to record cashing.")

            _assert_active_account(cursor, financial_account_id)
            existing_entries = _find_existing_cashing_entries(
                cursor,
                [collection_date],
                [entry["bus_id"] for entry in cleaned_entries],
            )
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            return _record_cashing_collection_with_cursor(
                cursor,
                collection_date,
                financial_account_id,
                cleaned_entries,
                notes,
            )


def record_direct_cashing_collection(
    collection_date: date,
    financial_account_id: int,
    entries: list[dict],
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_collection_date(collection_date)
    cleaned_entries = [
        _clean_direct_entry(entry)
        for entry in entries
        if entry.get("include")
    ]
    if not cleaned_entries:
        raise ValueError("Choose at least one bus.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            _assert_active_account(cursor, financial_account_id)
            existing_entries = _find_existing_cashing_entries(
                cursor,
                [collection_date],
                [entry["bus_id"] for entry in cleaned_entries],
            )
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            return _record_cashing_collection_with_cursor(
                cursor,
                collection_date,
                financial_account_id,
                cleaned_entries,
                notes,
            )


def record_cashing_backfill(
    financial_account_id: int,
    rows: list[dict],
    notes: str | None = None,
) -> list[dict]:
    included_rows = [row for row in rows if row.get("include")]
    if not included_rows:
        raise ValueError("Select at least one row to save.")

    grouped_entries: dict[date, list[dict]] = {}
    seen_pairs = set()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            _assert_active_account(cursor, financial_account_id)

            for row in included_rows:
                collection_date = _coerce_collection_date(row.get("collection_date"))
                bus_id = int(row["bus_id"])
                pair = (collection_date, bus_id)
                if pair in seen_pairs:
                    raise ValueError("The same bus appears more than once on the same date.")
                seen_pairs.add(pair)

                rates = _get_active_cashing_rates(cursor, collection_date)
                cleaned = _clean_entry(
                    {
                        "include": True,
                        "bus_id": bus_id,
                        "normal_days": row.get("normal_days"),
                        "sunday_days": row.get("sunday_days"),
                        "actual_amount": row.get("actual_amount"),
                        "explanation": row.get("explanation"),
                        "notes": row.get("notes"),
                    },
                    rates,
                )
                cleaned["normal_daily_rate"] = rates["NORMAL_DAY"]
                cleaned["sunday_rate"] = rates["SUNDAY"]
                grouped_entries.setdefault(collection_date, []).append(cleaned)

            collection_dates = sorted(grouped_entries)
            existing_entries = _find_existing_cashing_entries(
                cursor,
                collection_dates,
                [pair[1] for pair in seen_pairs],
            )
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            saved_collections = []
            for collection_date in collection_dates:
                saved_collections.append(
                    _record_cashing_collection_with_cursor(
                        cursor,
                        collection_date,
                        financial_account_id,
                        grouped_entries[collection_date],
                        notes,
                    )
                )

            return saved_collections


def update_cashing_collection(
    collection_id: int,
    collection_date: date,
    financial_account_id: int,
    entries: list[dict],
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_collection_date(collection_date)

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

            rates = _get_active_cashing_rates(cursor, collection_date)
            cleaned_entries = []
            for entry in entries:
                if entry.get("include"):
                    cleaned = _clean_entry(entry, rates)
                    cleaned["normal_daily_rate"] = rates["NORMAL_DAY"]
                    cleaned["sunday_rate"] = rates["SUNDAY"]
                    cleaned_entries.append(cleaned)

            if not cleaned_entries:
                raise ValueError("Select at least one bus to keep in this collection.")

            _assert_active_account(cursor, financial_account_id)
            cursor.execute(
                """
                SELECT
                    c.collection_date,
                    r.bus_id,
                    b.registration_number
                FROM remittance_collections c
                JOIN remittances r ON r.collection_id = c.id
                JOIN buses b ON b.id = r.bus_id
                WHERE c.id <> %s
                  AND c.collection_date = %s
                  AND r.bus_id = ANY(%s)
                ORDER BY c.collection_date, b.registration_number;
                """,
                (
                    collection_id,
                    collection_date,
                    [entry["bus_id"] for entry in cleaned_entries],
                ),
            )
            existing_entries = cursor.fetchall()
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            total_amount = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))
            financial_transaction_id = existing["financial_transaction_id"]

            if total_amount > 0 and financial_transaction_id is None:
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
                financial_transaction_id = cursor.fetchone()["id"]
            elif total_amount > 0:
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
                        financial_transaction_id,
                    ),
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
                    financial_transaction_id if total_amount > 0 else None,
                    clean_optional_text(notes),
                    collection_id,
                ),
            )
            collection = cursor.fetchone()

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

            if total_amount == 0 and financial_transaction_id is not None:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (financial_transaction_id,),
                )

            return collection


def update_direct_cashing_collection(
    collection_id: int,
    collection_date: date,
    financial_account_id: int,
    entries: list[dict],
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_collection_date(collection_date)

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

            cleaned_entries = [
                _clean_direct_entry(entry)
                for entry in entries
                if entry.get("include")
            ]
            if not cleaned_entries:
                raise ValueError("Choose at least one bus.")

            _assert_active_account(cursor, financial_account_id)
            cursor.execute(
                """
                SELECT
                    c.collection_date,
                    r.bus_id,
                    b.registration_number
                FROM remittance_collections c
                JOIN remittances r ON r.collection_id = c.id
                JOIN buses b ON b.id = r.bus_id
                WHERE c.id <> %s
                  AND c.collection_date = %s
                  AND r.bus_id = ANY(%s)
                ORDER BY c.collection_date, b.registration_number;
                """,
                (
                    collection_id,
                    collection_date,
                    [entry["bus_id"] for entry in cleaned_entries],
                ),
            )
            existing_entries = cursor.fetchall()
            if existing_entries:
                raise ValueError(_format_duplicate(existing_entries))

            total_amount = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))
            financial_transaction_id = existing["financial_transaction_id"]

            if total_amount > 0 and financial_transaction_id is None:
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
                financial_transaction_id = cursor.fetchone()["id"]
            else:
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
                        financial_transaction_id,
                    ),
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
