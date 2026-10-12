from datetime import date, timedelta

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import clean_optional_text, clean_required_text, parse_optional_positive_int


DOCUMENT_TYPES = {
    "INSURANCE",
    "ROAD_TAX",
    "FITNESS",
    "ROAD_SERVICE_LICENSE",
    "OTHER",
}


def get_all_buses():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT
                    b.id,
                    b.registration_number,
                    r.name AS route_name,
                    b.status,
                    b.model,
                    b.seating_capacity,
                    b.chassis_number,
                    b.date_acquired,
                    b.notes
                FROM buses b
                JOIN routes r ON b.route_id = r.id
                ORDER BY b.id;
            """)

            return cursor.fetchall()


def get_buses_overview(on_date=None, search=None, status=None):
    params = []
    where_clauses = []

    if status in {"ACTIVE", "INACTIVE"}:
        where_clauses.append("b.status = %s")
        params.append(status)

    if search:
        pattern = f"%{search.strip()}%"
        where_clauses.append(
            """
            (
                b.registration_number ILIKE %s
                OR r.name ILIKE %s
                OR assigned.full_name ILIKE %s
            )
            """
        )
        params.extend([pattern, pattern, pattern])

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT
                    b.id,
                    b.registration_number,
                    b.status,
                    b.model,
                    b.seating_capacity,
                    b.chassis_number,
                    b.date_acquired,
                    b.notes,
                    r.name AS route_name,
                    assigned.full_name AS driver_name,
                    documents.document_count,
                    documents.next_document_expiry
                FROM buses b
                JOIN routes r ON r.id = b.route_id
                LEFT JOIN LATERAL (
                    SELECT d.full_name
                    FROM driver_assignments da
                    JOIN driver_employments de ON de.id = da.employment_id
                    JOIN drivers d ON d.id = de.driver_id
                    WHERE da.bus_id = b.id
                      AND da.status = 'ACTIVE'
                      AND (%s::date IS NULL OR da.start_date <= %s::date)
                      AND (%s::date IS NULL OR da.end_date IS NULL OR da.end_date >= %s::date)
                      AND (%s::date IS NULL OR de.start_date <= %s::date)
                      AND (%s::date IS NULL OR de.end_date IS NULL OR de.end_date >= %s::date)
                    ORDER BY da.assignment_type = 'PERMANENT' DESC, da.start_date DESC
                    LIMIT 1
                ) assigned ON TRUE
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(*) AS document_count,
                        MIN(expiry_date) FILTER (WHERE expiry_date IS NOT NULL) AS next_document_expiry
                    FROM bus_documents bd
                    WHERE bd.bus_id = b.id
                ) documents ON TRUE
                {where_sql}
                ORDER BY b.registration_number;
                """,
                [
                    on_date,
                    on_date,
                    on_date,
                    on_date,
                    on_date,
                    on_date,
                    on_date,
                    on_date,
                    *params,
                ],
            )

            return cursor.fetchall()


def get_bus_details(bus_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    b.id,
                    b.registration_number,
                    b.route_id,
                    r.name AS route_name,
                    b.status,
                    b.model,
                    b.seating_capacity,
                    b.chassis_number,
                    b.date_acquired,
                    b.notes
                FROM buses b
                JOIN routes r ON r.id = b.route_id
                WHERE b.id = %s;
                """,
                (bus_id,),
            )
            bus = cursor.fetchone()
            if bus is None:
                raise ValueError("Bus not found.")

            cursor.execute(
                """
                SELECT id, status, effective_from, effective_to, reason
                FROM bus_status_history
                WHERE bus_id = %s
                ORDER BY effective_from DESC, id DESC;
                """,
                (bus_id,),
            )
            status_history = cursor.fetchall()

            cursor.execute(
                """
                SELECT brh.id, brh.route_id, r.name AS route_name,
                       brh.effective_from, brh.effective_to, brh.notes
                FROM bus_route_history brh
                JOIN routes r ON r.id = brh.route_id
                WHERE brh.bus_id = %s
                ORDER BY brh.effective_from DESC, brh.id DESC;
                """,
                (bus_id,),
            )
            route_history = cursor.fetchall()

            cursor.execute(
                """
                SELECT id, document_type, document_number, issue_date, expiry_date, notes
                FROM bus_documents
                WHERE bus_id = %s
                ORDER BY document_type, expiry_date NULLS LAST;
                """,
                (bus_id,),
            )
            documents = cursor.fetchall()

    return {
        "bus": bus,
        "status_history": status_history,
        "route_history": route_history,
        "documents": documents,
    }


def get_bus_status_history(bus_id: int) -> list[dict]:
    return get_bus_details(bus_id)["status_history"]


def _validate_route(cursor, route_id: int) -> None:
    cursor.execute(
        """
        SELECT id
        FROM routes
        WHERE id = %s
          AND active = TRUE;
        """,
        (route_id,),
    )
    if cursor.fetchone() is None:
        raise ValueError("Choose an active route.")


def _close_current_status(cursor, bus_id: int, effective_date: date) -> dict | None:
    cursor.execute(
        """
        SELECT id, status, effective_from
        FROM bus_status_history
        WHERE bus_id = %s
          AND effective_to IS NULL
        FOR UPDATE;
        """,
        (bus_id,),
    )
    current = cursor.fetchone()
    if current is None:
        return None
    if effective_date <= current["effective_from"]:
        raise ValueError("Use a status effective date after the current status start date.")
    cursor.execute(
        """
        UPDATE bus_status_history
        SET effective_to = %s
        WHERE id = %s;
        """,
        (effective_date - timedelta(days=1), current["id"]),
    )
    return current


def _close_current_route(cursor, bus_id: int, effective_date: date) -> dict | None:
    cursor.execute(
        """
        SELECT id, route_id, effective_from
        FROM bus_route_history
        WHERE bus_id = %s
          AND effective_to IS NULL
        FOR UPDATE;
        """,
        (bus_id,),
    )
    current = cursor.fetchone()
    if current is None:
        return None
    if effective_date <= current["effective_from"]:
        raise ValueError("Use a route effective date after the current route start date.")
    cursor.execute(
        """
        UPDATE bus_route_history
        SET effective_to = %s
        WHERE id = %s;
        """,
        (effective_date - timedelta(days=1), current["id"]),
    )
    return current


def update_bus(
    bus_id: int,
    registration_number: str,
    route_id: int,
    route_effective_date: date,
    model: str | None = None,
    seating_capacity=None,
    chassis_number: str | None = None,
    date_acquired: date | None = None,
    notes: str | None = None,
) -> dict:
    registration = clean_required_text(registration_number, "Registration number").upper()
    seats = parse_optional_positive_int(seating_capacity, "Seating capacity")
    if not isinstance(route_effective_date, date):
        raise ValueError("Route effective date is required.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            _validate_route(cursor, route_id)
            cursor.execute(
                """
                SELECT id, route_id
                FROM buses
                WHERE id = %s
                FOR UPDATE;
                """,
                (bus_id,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise ValueError("Bus not found.")

            if existing["route_id"] != route_id:
                _close_current_route(cursor, bus_id, route_effective_date)
                cursor.execute(
                    """
                    INSERT INTO bus_route_history (bus_id, route_id, effective_from, notes)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (bus_id, route_id, route_effective_date, "Route updated from Buses page"),
                )

            cursor.execute(
                """
                UPDATE buses
                SET registration_number = %s,
                    route_id = %s,
                    model = %s,
                    seating_capacity = %s,
                    chassis_number = %s,
                    date_acquired = %s,
                    notes = %s
                WHERE id = %s
                RETURNING id, registration_number, route_id, status, model,
                          seating_capacity, chassis_number, date_acquired, notes;
                """,
                (
                    registration,
                    route_id,
                    clean_optional_text(model),
                    seats,
                    clean_optional_text(chassis_number),
                    date_acquired,
                    clean_optional_text(notes),
                    bus_id,
                ),
            )
            return cursor.fetchone()


def set_bus_status(
    bus_id: int,
    status: str,
    effective_date: date,
    reason: str | None = None,
) -> dict:
    if status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("Bus status must be Active or Deactivated.")
    if not isinstance(effective_date, date):
        raise ValueError("Status effective date is required.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, status
                FROM buses
                WHERE id = %s
                FOR UPDATE;
                """,
                (bus_id,),
            )
            bus = cursor.fetchone()
            if bus is None:
                raise ValueError("Bus not found.")
            if bus["status"] == status:
                raise ValueError("Bus already has that status.")

            _close_current_status(cursor, bus_id, effective_date)
            cursor.execute(
                """
                INSERT INTO bus_status_history (bus_id, status, effective_from, reason)
                VALUES (%s, %s, %s, %s);
                """,
                (bus_id, status, effective_date, clean_optional_text(reason)),
            )
            cursor.execute(
                """
                UPDATE buses
                SET status = %s
                WHERE id = %s
                RETURNING id, registration_number, status;
                """,
                (status, bus_id),
            )
            return cursor.fetchone()


def _period_days(start_date: date, end_date: date) -> list[date]:
    days = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def count_active_days_from_history(
    history_rows: list[dict],
    start_date: date,
    end_date: date,
) -> int:
    total = 0
    for day in _period_days(start_date, end_date):
        active = False
        for row in history_rows:
            row_end = row.get("effective_to")
            if row["effective_from"] <= day and (row_end is None or row_end >= day):
                active = row["status"] == "ACTIVE"
                break
        if active:
            total += 1
    return total


def get_bus_active_day_counts(start_date: date, end_date: date, bus_ids: list[int] | None = None) -> dict[int, int]:
    params: list = [start_date, end_date, end_date, start_date]
    bus_filter = ""
    if bus_ids:
        bus_filter = "AND b.id = ANY(%s)"
        params.append(bus_ids)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT
                    b.id AS bus_id,
                    COALESCE(
                        COUNT(days.day) FILTER (WHERE bsh.status = 'ACTIVE'),
                        0
                    ) AS active_days
                FROM buses b
                LEFT JOIN LATERAL generate_series(%s::date, %s::date, INTERVAL '1 day') AS days(day)
                    ON TRUE
                LEFT JOIN bus_status_history bsh
                    ON bsh.bus_id = b.id
                   AND bsh.effective_from <= days.day
                   AND (bsh.effective_to IS NULL OR bsh.effective_to >= days.day)
                WHERE EXISTS (
                    SELECT 1
                    FROM bus_status_history h
                    WHERE h.bus_id = b.id
                      AND h.status = 'ACTIVE'
                      AND h.effective_from <= %s
                      AND (h.effective_to IS NULL OR h.effective_to >= %s)
                )
                {bus_filter}
                GROUP BY b.id
                ORDER BY b.id;
                """,
                params,
            )
            return {row["bus_id"]: int(row["active_days"]) for row in cursor.fetchall()}


def _clean_document_records(document_records: list[dict] | None) -> list[dict]:
    cleaned_records = []
    for record in document_records or []:
        document_type = record.get("document_type")
        if document_type not in DOCUMENT_TYPES:
            raise ValueError("Document type is not supported.")

        document_number = clean_optional_text(record.get("document_number"))
        notes = clean_optional_text(record.get("notes"))
        issue_date = record.get("issue_date")
        expiry_date = record.get("expiry_date")

        if document_number or notes or issue_date or expiry_date:
            cleaned_records.append(
                {
                    "document_type": document_type,
                    "document_number": document_number,
                    "issue_date": issue_date,
                    "expiry_date": expiry_date,
                    "notes": notes,
                }
            )

    return cleaned_records


def create_bus(
    registration_number,
    route_id,
    status="ACTIVE",
    date_acquired=None,
    notes=None,
    employment_id=None,
    model=None,
    seating_capacity=None,
    chassis_number=None,
    document_records=None,
):
    registration = clean_required_text(registration_number, "Registration number").upper()
    if status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("Initial status must be Active or Deactivated.")
    seats = parse_optional_positive_int(seating_capacity, "Seating capacity")
    documents = _clean_document_records(document_records)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO buses (
                    registration_number,
                    route_id,
                    status,
                    date_acquired,
                    notes,
                    model,
                    seating_capacity,
                    chassis_number
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    registration_number,
                    route_id,
                    status,
                    date_acquired,
                    notes,
                    model,
                    seating_capacity,
                    chassis_number;
                """,
                (
                    registration,
                    route_id,
                    status,
                    date_acquired,
                    clean_optional_text(notes),
                    clean_optional_text(model),
                    seats,
                    clean_optional_text(chassis_number),
                ),
            )
            bus = cursor.fetchone()

            if employment_id is not None:
                cursor.execute(
                    """
                    INSERT INTO driver_assignments (
                        employment_id,
                        bus_id,
                        assignment_type,
                        start_date,
                        status,
                        notes
                    )
                    VALUES (%s, %s, 'PERMANENT', COALESCE(%s, CURRENT_DATE), 'ACTIVE', %s);
                    """,
                    (employment_id, bus["id"], date_acquired, "Initial assignment created from Add Bus"),
                )

            for document in documents:
                cursor.execute(
                    """
                    INSERT INTO bus_documents (
                        bus_id,
                        document_type,
                        document_number,
                        issue_date,
                        expiry_date,
                        notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (
                        bus["id"],
                        document["document_type"],
                        document["document_number"],
                        document["issue_date"],
                        document["expiry_date"],
                        document["notes"],
                    ),
                )

            cursor.execute(
                """
                INSERT INTO bus_status_history (bus_id, status, effective_from, reason)
                VALUES (%s, %s, COALESCE(%s, CURRENT_DATE), %s);
                """,
                (bus["id"], status, date_acquired, "Initial status created from Add Bus"),
            )
            cursor.execute(
                """
                INSERT INTO bus_route_history (bus_id, route_id, effective_from, notes)
                VALUES (%s, %s, COALESCE(%s, CURRENT_DATE), %s);
                """,
                (bus["id"], route_id, date_acquired, "Initial route created from Add Bus"),
            )

            return bus
