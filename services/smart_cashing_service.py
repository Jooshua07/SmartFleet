from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from psycopg.rows import dict_row

from database.connection import get_connection
from services import bus_service
from services.cashing_service import get_cashing_rates_for_date
from utils.validation import clean_optional_text, clean_required_text, parse_non_negative_amount


DIFFERENCE_CLASSIFICATIONS = {
    "MATCHED",
    "UNKNOWN_DIFFERENCE",
    "SURPLUS",
    "REDUCED_WORKDAYS",
    "UNDERPERFORMANCE",
    "CONFIRMED_UNPAID_OBLIGATION",
}


def _coerce_date(value, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"{field_name} is required.")


def _money(value, field_name: str, allow_negative: bool = False) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid amount.") from exc
    if not amount.is_finite():
        raise ValueError(f"{field_name} must be a valid amount.")
    if amount < 0 and not allow_negative:
        raise ValueError(f"{field_name} cannot be negative.")
    return amount


def get_collection_coverage(collection_date: date, schedule_rules=None) -> dict:
    collection_date = _coerce_date(collection_date, "Collection date")
    if schedule_rules is not None:
        from services.collection_schedule_service import coverage_from_rules
        return coverage_from_rules(collection_date, schedule_rules)
    weekday = collection_date.isoweekday()
    if weekday == 7:
        return {
            "collection_type": "SUNDAY",
            "coverage_start": collection_date - timedelta(days=3),
            "coverage_end": collection_date - timedelta(days=1),
            "previous_sunday": None,
        }
    if weekday == 4:
        return {
            "collection_type": "THURSDAY",
            "coverage_start": collection_date - timedelta(days=3),
            "coverage_end": collection_date - timedelta(days=1),
            "previous_sunday": collection_date - timedelta(days=4),
        }
    raise ValueError("Choose a Thursday or Sunday collection date, or use Backfill with one of those dates.")


def _load_bus_rows(bus_ids: list[int]) -> list[dict]:
    if not bus_ids:
        return []
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    b.id,
                    b.registration_number,
                    b.status,
                    r.name AS route_name,
                    assigned.full_name AS driver_name,
                    assigned.driver_id
                FROM buses b
                JOIN routes r ON r.id = b.route_id
                LEFT JOIN LATERAL (
                    SELECT d.id AS driver_id, d.full_name
                    FROM driver_assignments da
                    JOIN driver_employments de ON de.id = da.employment_id
                    JOIN drivers d ON d.id = de.driver_id
                    WHERE da.bus_id = b.id
                      AND da.status = 'ACTIVE'
                    ORDER BY da.assignment_type = 'PERMANENT' DESC, da.start_date DESC
                    LIMIT 1
                ) assigned ON TRUE
                WHERE b.id = ANY(%s)
                ORDER BY b.registration_number;
                """,
                (bus_ids,),
            )
            return cursor.fetchall()


def get_smart_cashing_preview(collection_date: date, schedule_rules=None) -> dict:
    coverage = get_collection_coverage(collection_date, schedule_rules=schedule_rules)
    rates = get_cashing_rates_for_date(collection_date)
    active_days = bus_service.get_bus_active_day_counts(coverage["coverage_start"], coverage["coverage_end"])
    buses = _load_bus_rows(list(active_days))

    bus_rows = []
    for bus in buses:
        normal_days = active_days.get(bus["id"], 0)
        if normal_days <= 0:
            continue
        expected = Decimal(normal_days) * rates["NORMAL_DAY"]
        bus_rows.append(
            {
                **bus,
                "normal_days": normal_days,
                "sunday_days": 0,
                "normal_daily_rate": rates["NORMAL_DAY"],
                "sunday_rate": rates["SUNDAY"],
                "expected_amount": expected,
            }
        )

    expected_total = sum((bus["expected_amount"] for bus in bus_rows), Decimal("0.00"))
    return {
        **coverage,
        "rates": rates,
        "buses": bus_rows,
        "expected_total": expected_total,
    }


def build_standard_allocations(
    preview: dict,
    selected_bus_ids: list[int],
    sunday_bus_ids: list[int],
    total_received,
    difference_classification: str | None = None,
) -> dict:
    total_received = _money(total_received, "Actual received")
    if not selected_bus_ids:
        raise ValueError("Choose at least one bus.")

    selected = [bus for bus in preview["buses"] if bus["id"] in set(selected_bus_ids)]
    if not selected:
        raise ValueError("Choose at least one eligible bus.")

    entries = []
    expected_total = Decimal("0.00")
    for bus in selected:
        sunday_days = 1 if bus["id"] in set(sunday_bus_ids) else 0
        expected = (
            Decimal(bus["normal_days"]) * bus["normal_daily_rate"]
            + Decimal(sunday_days) * bus["sunday_rate"]
        )
        expected_total += expected
        entries.append(
            {
                "bus_id": bus["id"],
                "normal_days": bus["normal_days"],
                "normal_daily_rate": bus["normal_daily_rate"],
                "sunday_days": sunday_days,
                "sunday_rate": bus["sunday_rate"],
                "actual_amount": expected,
                "allocation_provenance": "ESTIMATED_STANDARD",
                "difference_classification": "MATCHED",
                "worked_days_adjusted": False,
                "sunday_worked": sunday_days > 0,
                "explanation": None,
                "notes": None,
            }
        )

    unallocated_amount = total_received - expected_total
    if unallocated_amount == 0:
        collection_classification = "MATCHED"
    elif unallocated_amount > 0:
        collection_classification = "SURPLUS"
    else:
        collection_classification = difference_classification or "UNKNOWN_DIFFERENCE"
        if collection_classification not in {"UNKNOWN_DIFFERENCE", "UNDERPERFORMANCE", "CONFIRMED_UNPAID_OBLIGATION"}:
            raise ValueError("Choose a valid shortage classification.")

    return {
        "entries": entries,
        "expected_total": expected_total,
        "unallocated_amount": unallocated_amount,
        "difference_classification": collection_classification,
    }


def _clean_smart_entry(entry: dict) -> dict:
    classification = entry.get("difference_classification") or "MATCHED"
    if classification not in DIFFERENCE_CLASSIFICATIONS:
        raise ValueError("Cashing difference classification is not supported.")

    normal_days = int(entry.get("normal_days") or 0)
    sunday_days = int(entry.get("sunday_days") or 0)
    if normal_days < 0 or sunday_days < 0:
        raise ValueError("Worked days cannot be negative.")

    cleaned = {
        "bus_id": int(entry["bus_id"]),
        "normal_days": normal_days,
        "normal_daily_rate": parse_non_negative_amount(entry.get("normal_daily_rate", 0), "Normal rate"),
        "sunday_days": sunday_days,
        "sunday_rate": parse_non_negative_amount(entry.get("sunday_rate", 0), "Sunday rate"),
        "actual_amount": parse_non_negative_amount(entry.get("actual_amount", 0), "Bus allocation"),
        "allocation_provenance": entry.get("allocation_provenance") or "MANUAL_ADJUSTMENT",
        "difference_classification": classification,
        "worked_days_adjusted": bool(entry.get("worked_days_adjusted")),
        "sunday_worked": bool(entry.get("sunday_worked")) or sunday_days > 0,
        "explanation": clean_optional_text(entry.get("explanation")),
        "notes": clean_optional_text(entry.get("notes")),
        "obligation": entry.get("obligation"),
    }
    if cleaned["allocation_provenance"] not in {
        "CONFIRMED_ACTUAL",
        "ESTIMATED_STANDARD",
        "MANUAL_ADJUSTMENT",
    }:
        raise ValueError("Allocation provenance is not supported.")
    return cleaned


def _entry_expected(entry: dict) -> Decimal:
    return (
        Decimal(entry["normal_days"]) * entry["normal_daily_rate"]
        + Decimal(entry["sunday_days"]) * entry["sunday_rate"]
    )


def _assert_airtel_account(cursor, financial_account_id: int, message: str = "Cashing must be paid into Airtel Money.") -> None:
    cursor.execute(
        """
        SELECT id
        FROM financial_accounts
        WHERE id = %s
          AND active = TRUE
          AND account_type = 'AIRTEL_MONEY';
        """,
        (financial_account_id,),
    )
    if cursor.fetchone() is None:
        raise ValueError(message)


def _find_existing_entries(
    cursor,
    collection_date: date,
    bus_ids: list[int],
    exclude_collection_id: int | None = None,
) -> list[dict]:
    excluded_clause = ""
    params: list = [collection_date, bus_ids]
    if exclude_collection_id is not None:
        excluded_clause = "AND c.id <> %s"
        params.append(exclude_collection_id)

    cursor.execute(
        f"""
        SELECT b.registration_number, c.collection_date
        FROM remittance_collections c
        JOIN remittances r ON r.collection_id = c.id
        JOIN buses b ON b.id = r.bus_id
        WHERE c.collection_date = %s
          AND r.bus_id = ANY(%s)
          {excluded_clause}
        ORDER BY b.registration_number;
        """,
        params,
    )
    return cursor.fetchall()


def _assert_collection_can_be_corrected(cursor, collection_id: int) -> None:
    cursor.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE o.status <> 'VOID') AS active_obligations,
            COUNT(p.id) AS payment_count
        FROM cashing_obligations o
        LEFT JOIN cashing_obligation_payments p ON p.obligation_id = o.id
        WHERE o.collection_id = %s;
        """,
        (collection_id,),
    )
    lock = cursor.fetchone()
    if lock["active_obligations"] > 0 or lock["payment_count"] > 0:
        raise ValueError(
            "This cashing has obligations or payments. Use the obligation records instead of editing it."
        )


def _insert_smart_rows(
    cursor,
    collection_id: int,
    collection_date: date,
    cleaned_entries: list[dict],
) -> None:
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
                notes,
                allocation_provenance,
                difference_classification,
                worked_days_adjusted,
                sunday_worked
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, expected_amount;
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
                entry["allocation_provenance"],
                entry["difference_classification"],
                entry["worked_days_adjusted"],
                entry["sunday_worked"],
            ),
        )
        remittance = cursor.fetchone()
        if entry["difference_classification"] == "CONFIRMED_UNPAID_OBLIGATION":
            obligation = entry.get("obligation") or {}
            responsible_name = clean_required_text(
                obligation.get("responsible_party_name"),
                "Responsible party",
            )
            responsible_type = obligation.get("responsible_party_type") or "OTHER"
            if responsible_type not in {"HEAD_DRIVER", "ASSIGNED_DRIVER", "OTHER"}:
                raise ValueError("Responsible party type is not supported.")
            amount = _money(
                obligation.get("amount", remittance["expected_amount"] - entry["actual_amount"]),
                "Obligation amount",
            )
            if amount <= 0:
                raise ValueError("Confirmed obligation amount must be greater than zero.")
            cursor.execute(
                """
                INSERT INTO cashing_obligations (
                    collection_id,
                    remittance_id,
                    amount,
                    outstanding_amount,
                    responsible_party_type,
                    responsible_party_name,
                    driver_id,
                    recognized_date,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    collection_id,
                    remittance["id"],
                    amount,
                    amount,
                    responsible_type,
                    responsible_name,
                    obligation.get("driver_id"),
                    collection_date,
                    clean_optional_text(obligation.get("notes")),
                ),
            )


def record_smart_cashing_collection(
    collection_date: date,
    financial_account_id: int,
    total_received,
    entries: list[dict],
    unallocated_amount=0,
    difference_classification: str = "MATCHED",
    cashing_mode: str = "STANDARD",
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_date(collection_date, "Collection date")
    coverage = get_collection_coverage(collection_date)
    total_received = _money(total_received, "Actual received")
    unallocated_amount = _money(unallocated_amount, "Unallocated amount", allow_negative=True)
    if difference_classification not in DIFFERENCE_CLASSIFICATIONS:
        raise ValueError("Collection difference classification is not supported.")
    if cashing_mode not in {"STANDARD", "ADJUSTED"}:
        raise ValueError("Cashing mode is not supported.")

    cleaned_entries = [_clean_smart_entry(entry) for entry in entries]
    if not cleaned_entries:
        raise ValueError("Choose at least one bus.")

    allocation_total = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))
    if allocation_total + unallocated_amount != total_received:
        raise ValueError("Bus allocations plus unallocated amount must equal actual received.")
    expected_total = sum((_entry_expected(entry) for entry in cleaned_entries), Decimal("0.00"))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            _assert_airtel_account(cursor, financial_account_id)
            existing = _find_existing_entries(
                cursor,
                collection_date,
                [entry["bus_id"] for entry in cleaned_entries],
            )
            if existing:
                first = existing[0]
                raise ValueError(
                    f"Cashing already exists for {first['registration_number']} on "
                    f"{first['collection_date']:%d/%m/%Y}."
                )

            financial_transaction_id = None
            if total_received > 0:
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
                        total_received,
                        "Smart cashing collection",
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
                    notes,
                    coverage_start,
                    coverage_end,
                    expected_total,
                    unallocated_amount,
                    cashing_mode,
                    difference_classification
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, collection_date, total_amount, expected_total, unallocated_amount;
                """,
                (
                    collection_date,
                    financial_account_id,
                    total_received,
                    financial_transaction_id,
                    clean_optional_text(notes),
                    coverage["coverage_start"],
                    coverage["coverage_end"],
                    expected_total,
                    unallocated_amount,
                    cashing_mode,
                    difference_classification,
                ),
            )
            collection = cursor.fetchone()

            _insert_smart_rows(cursor, collection["id"], collection_date, cleaned_entries)
            return collection


def update_smart_cashing_collection(
    collection_id: int,
    collection_date: date,
    financial_account_id: int,
    total_received,
    entries: list[dict],
    unallocated_amount=0,
    difference_classification: str = "MATCHED",
    cashing_mode: str = "ADJUSTED",
    notes: str | None = None,
) -> dict:
    collection_date = _coerce_date(collection_date, "Collection date")
    coverage = get_collection_coverage(collection_date)
    total_received = _money(total_received, "Actual received")
    unallocated_amount = _money(unallocated_amount, "Unallocated amount", allow_negative=True)
    if difference_classification not in DIFFERENCE_CLASSIFICATIONS:
        raise ValueError("Collection difference classification is not supported.")
    if cashing_mode not in {"STANDARD", "ADJUSTED"}:
        raise ValueError("Cashing mode is not supported.")

    cleaned_entries = [_clean_smart_entry(entry) for entry in entries]
    if not cleaned_entries:
        raise ValueError("Choose at least one bus.")

    allocation_total = sum((entry["actual_amount"] for entry in cleaned_entries), Decimal("0.00"))
    if allocation_total + unallocated_amount != total_received:
        raise ValueError("Bus allocations plus unallocated amount must equal actual received.")
    expected_total = sum((_entry_expected(entry) for entry in cleaned_entries), Decimal("0.00"))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT financial_transaction_id, cashing_mode
                FROM remittance_collections
                WHERE id = %s
                FOR UPDATE;
                """,
                (collection_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Cashing collection not found.")
            if existing["cashing_mode"] == "DIRECT":
                raise ValueError("Use the direct cashing editor for direct cashing records.")

            _assert_collection_can_be_corrected(cursor, collection_id)
            _assert_airtel_account(cursor, financial_account_id)
            duplicate_entries = _find_existing_entries(
                cursor,
                collection_date,
                [entry["bus_id"] for entry in cleaned_entries],
                exclude_collection_id=collection_id,
            )
            if duplicate_entries:
                first = duplicate_entries[0]
                raise ValueError(
                    f"Cashing already exists for {first['registration_number']} on "
                    f"{first['collection_date']:%d/%m/%Y}."
                )

            financial_transaction_id = existing["financial_transaction_id"]
            if total_received > 0:
                if financial_transaction_id is None:
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
                            total_received,
                            "Smart cashing correction",
                            clean_optional_text(notes),
                        ),
                    )
                    financial_transaction_id = cursor.fetchone()["id"]
                else:
                    cursor.execute(
                        """
                        UPDATE financial_transactions
                        SET account_id = %s,
                            transaction_date = %s,
                            amount = %s,
                            description = %s,
                            notes = %s
                        WHERE id = %s;
                        """,
                        (
                            financial_account_id,
                            collection_date,
                            total_received,
                            "Smart cashing correction",
                            clean_optional_text(notes),
                            financial_transaction_id,
                        ),
                    )
            else:
                financial_transaction_id = None

            cursor.execute("DELETE FROM remittances WHERE collection_id = %s;", (collection_id,))
            cursor.execute(
                """
                UPDATE remittance_collections
                SET collection_date = %s,
                    financial_account_id = %s,
                    total_amount = %s,
                    financial_transaction_id = %s,
                    notes = %s,
                    coverage_start = %s,
                    coverage_end = %s,
                    expected_total = %s,
                    unallocated_amount = %s,
                    cashing_mode = %s,
                    difference_classification = %s
                WHERE id = %s
                RETURNING id, collection_date, total_amount, expected_total, unallocated_amount;
                """,
                (
                    collection_date,
                    financial_account_id,
                    total_received,
                    financial_transaction_id,
                    clean_optional_text(notes),
                    coverage["coverage_start"],
                    coverage["coverage_end"],
                    expected_total,
                    unallocated_amount,
                    cashing_mode,
                    difference_classification,
                    collection_id,
                ),
            )
            collection = cursor.fetchone()
            if existing["financial_transaction_id"] is not None and total_received == 0:
                cursor.execute(
                    "DELETE FROM financial_transactions WHERE id = %s;",
                    (existing["financial_transaction_id"],),
                )
            _insert_smart_rows(cursor, collection_id, collection_date, cleaned_entries)
            return collection


def record_obligation_payment(
    obligation_id: int,
    payment_date: date,
    amount,
    financial_account_id: int,
    notes: str | None = None,
) -> dict:
    payment_date = _coerce_date(payment_date, "Payment date")
    amount = _money(amount, "Payment amount")
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, outstanding_amount, status
                FROM cashing_obligations
                WHERE id = %s
                FOR UPDATE;
                """,
                (obligation_id,),
            )
            obligation = cursor.fetchone()
            if obligation is None:
                raise ValueError("Cashing obligation not found.")
            if obligation["status"] == "VOID":
                raise ValueError("This cashing obligation has been voided.")
            if obligation["outstanding_amount"] <= 0:
                raise ValueError("This cashing obligation is already settled.")
            if amount > obligation["outstanding_amount"]:
                raise ValueError("Payment cannot exceed the outstanding amount.")

            cursor.execute(
                """
                SELECT id
                FROM financial_accounts
                WHERE id = %s
                  AND active = TRUE
                  AND account_type = 'AIRTEL_MONEY';
                """,
                (financial_account_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Obligation payment must be paid into Airtel Money.")

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
                VALUES (%s, %s, 'OTHER', 'IN', %s, %s, %s)
                RETURNING id;
                """,
                (
                    financial_account_id,
                    payment_date,
                    amount,
                    "Cashing obligation repayment",
                    clean_optional_text(notes),
                ),
            )
            financial_transaction_id = cursor.fetchone()["id"]

            cursor.execute(
                """
                INSERT INTO cashing_obligation_payments (
                    obligation_id,
                    payment_date,
                    amount,
                    financial_account_id,
                    financial_transaction_id,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, obligation_id, amount;
                """,
                (
                    obligation_id,
                    payment_date,
                    amount,
                    financial_account_id,
                    financial_transaction_id,
                    clean_optional_text(notes),
                ),
            )
            payment = cursor.fetchone()

            new_outstanding = obligation["outstanding_amount"] - amount
            status = "SETTLED" if new_outstanding == 0 else "PARTIALLY_SETTLED"
            cursor.execute(
                """
                UPDATE cashing_obligations
                SET outstanding_amount = %s,
                    status = %s
                WHERE id = %s;
                """,
                (new_outstanding, status, obligation_id),
            )
            return payment


def list_open_cashing_obligations(limit: int = 20) -> list[dict]:
    limit = max(int(limit or 20), 1)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    o.id,
                    o.collection_id,
                    o.remittance_id,
                    o.amount,
                    o.outstanding_amount,
                    o.responsible_party_type,
                    o.responsible_party_name,
                    o.recognized_date,
                    o.status,
                    o.notes,
                    c.collection_date,
                    b.registration_number,
                    r.expected_amount,
                    r.actual_amount,
                    paid.paid_amount
                FROM cashing_obligations o
                JOIN remittance_collections c ON c.id = o.collection_id
                JOIN remittances r ON r.id = o.remittance_id
                JOIN buses b ON b.id = r.bus_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(SUM(p.amount), 0) AS paid_amount
                    FROM cashing_obligation_payments p
                    WHERE p.obligation_id = o.id
                ) paid ON TRUE
                WHERE o.status IN ('OPEN', 'PARTIALLY_SETTLED')
                  AND o.outstanding_amount > 0
                ORDER BY o.recognized_date DESC, o.id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cursor.fetchall()


def get_cashing_obligations_for_collection(collection_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    o.id,
                    o.collection_id,
                    o.remittance_id,
                    o.amount,
                    o.outstanding_amount,
                    o.responsible_party_type,
                    o.responsible_party_name,
                    o.recognized_date,
                    o.status,
                    o.notes,
                    b.registration_number,
                    r.expected_amount,
                    r.actual_amount,
                    paid.paid_amount
                FROM cashing_obligations o
                JOIN remittances r ON r.id = o.remittance_id
                JOIN buses b ON b.id = r.bus_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(SUM(p.amount), 0) AS paid_amount
                    FROM cashing_obligation_payments p
                    WHERE p.obligation_id = o.id
                ) paid ON TRUE
                WHERE o.collection_id = %s
                ORDER BY b.registration_number, o.id;
                """,
                (collection_id,),
            )
            return cursor.fetchall()


def list_cashing_obligation_payments(obligation_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.payment_date,
                    p.amount,
                    p.notes,
                    fa.name AS account_name
                FROM cashing_obligation_payments p
                JOIN financial_accounts fa ON fa.id = p.financial_account_id
                WHERE p.obligation_id = %s
                ORDER BY p.payment_date DESC, p.id DESC;
                """,
                (obligation_id,),
            )
            return cursor.fetchall()

