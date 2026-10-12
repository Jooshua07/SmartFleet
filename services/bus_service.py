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

            return bus
