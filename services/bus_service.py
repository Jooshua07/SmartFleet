from psycopg.rows import dict_row
from database.connection import get_connection
from utils.validation import clean_required_text


def get_all_buses():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT
                    b.id,
                    b.registration_number,
                    r.name AS route_name,
                    b.status,
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
                    b.date_acquired,
                    b.notes,
                    r.name AS route_name,
                    assigned.full_name AS driver_name
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


def create_bus(registration_number, route_id, status="ACTIVE", date_acquired=None, notes=None, employment_id=None):
    registration = clean_required_text(registration_number, "Registration number").upper()
    if status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("Initial status must be Active or Deactivated.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO buses (registration_number, route_id, status, date_acquired, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, registration_number, route_id, status, date_acquired, notes;
                """,
                (registration, route_id, status, date_acquired, notes),
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

            return bus
