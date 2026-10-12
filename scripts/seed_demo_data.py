from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _last_sunday(today: date) -> date:
    return today - timedelta(days=today.isoweekday() % 7)


def _fetch_id(cursor, table: str, column: str, value: str) -> int:
    cursor.execute(f"SELECT id FROM {table} WHERE {column} = %s;", (value,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Missing seed row: {table}.{column}={value}")
    return row["id"]


def _insert_financial_transaction(
    cursor,
    account_id: int,
    transaction_date: date,
    transaction_type: str,
    direction: str,
    amount: Decimal,
    description: str,
    notes: str | None = None,
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
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            account_id,
            transaction_date,
            transaction_type,
            direction,
            amount,
            description,
            notes,
        ),
    )
    return cursor.fetchone()["id"]


def _insert_cashing_collection(
    cursor,
    collection_date: date,
    account_id: int,
    buses: list[dict],
    normal_days: int,
    sunday_days: int,
    adjustments: dict[str, Decimal],
) -> None:
    normal_rate = Decimal("600.00")
    sunday_rate = Decimal("300.00")
    entries = []

    for bus in buses:
        expected = Decimal(normal_days) * normal_rate + Decimal(sunday_days) * sunday_rate
        adjustment = adjustments.get(bus["registration_number"], Decimal("0.00"))
        actual = expected + adjustment
        explanation = None
        if adjustment != 0:
            explanation = "Demo variance for testing edit and warning flows"
        entries.append(
            {
                "bus_id": bus["id"],
                "registration_number": bus["registration_number"],
                "expected": expected,
                "actual": actual,
                "explanation": explanation,
            }
        )

    total_amount = sum((entry["actual"] for entry in entries), Decimal("0.00"))
    transaction_id = _insert_financial_transaction(
        cursor,
        account_id,
        collection_date,
        "CASHING",
        "IN",
        total_amount,
        "Demo cashing collection",
        "Demo data only",
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
        RETURNING id;
        """,
        (collection_date, account_id, total_amount, transaction_id, "Demo data only"),
    )
    collection_id = cursor.fetchone()["id"]

    for entry in entries:
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
                normal_days,
                normal_rate,
                sunday_days,
                sunday_rate,
                entry["actual"],
                entry["explanation"],
                "Demo remittance row",
            ),
        )


def _insert_expense(
    cursor,
    expense_date: date,
    category_id: int,
    account_id: int,
    amount: Decimal,
    description: str,
    vendor_name: str,
    reference_number: str,
    bus_id: int | None = None,
) -> None:
    transaction_id = _insert_financial_transaction(
        cursor,
        account_id,
        expense_date,
        "EXPENSE",
        "OUT",
        amount,
        description,
        "Demo data only",
    )
    cursor.execute(
        """
        INSERT INTO expenses (
            expense_date,
            category_id,
            amount,
            description,
            scope,
            bus_id,
            payment_source,
            financial_account_id,
            financial_transaction_id,
            notes,
            vendor_name,
            reference_number
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'BUSINESS_ACCOUNT', %s, %s, %s, %s, %s);
        """,
        (
            expense_date,
            category_id,
            amount,
            description,
            "BUS" if bus_id is not None else "GENERAL",
            bus_id,
            account_id,
            transaction_id,
            "Demo data only",
            vendor_name,
            reference_number,
        ),
    )


def seed_demo_database(database_name: str) -> None:
    os.environ["DB_NAME"] = database_name

    from psycopg.rows import dict_row

    from database.connection import get_connection
    from utils.dates import today_lusaka

    today = today_lusaka()
    last_sunday = _last_sunday(today)
    current_thursday = last_sunday - timedelta(days=3)
    previous_sunday = last_sunday - timedelta(days=7)
    previous_thursday = current_thursday - timedelta(days=7)
    acquired_date = previous_thursday - timedelta(days=45)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            route_specs = [
                ("Demo Town Service", "Demo route for phone testing"),
                ("Demo Market Loop", "Demo route for phone testing"),
            ]
            route_ids = {}
            for name, description in route_specs:
                cursor.execute(
                    """
                    INSERT INTO routes (name, description)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (name, description),
                )
                route_ids[name] = cursor.fetchone()["id"]

            driver_specs = [
                ("Demo Driver One", "0970000001"),
                ("Demo Driver Two", "0970000002"),
                ("Demo Driver Three", "0970000003"),
                ("Demo Driver Four", "0970000004"),
            ]
            employment_ids = []
            for full_name, phone in driver_specs:
                cursor.execute(
                    """
                    INSERT INTO drivers (full_name, phone, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (full_name, phone, "Demo data only"),
                )
                driver_id = cursor.fetchone()["id"]
                cursor.execute(
                    """
                    INSERT INTO driver_employments (
                        driver_id,
                        start_date,
                        status,
                        monthly_salary,
                        notes
                    )
                    VALUES (%s, %s, 'ACTIVE', %s, %s)
                    RETURNING id;
                    """,
                    (driver_id, acquired_date, Decimal("2200.00"), "Demo data only"),
                )
                employment_ids.append(cursor.fetchone()["id"])

            bus_specs = [
                ("DEMO-101", "Toyota Hiace", 16, "Demo Town Service"),
                ("DEMO-102", "Toyota Hiace", 16, "Demo Town Service"),
                ("DEMO-103", "Nissan Caravan", 15, "Demo Market Loop"),
                ("DEMO-104", "Toyota Quantum", 16, "Demo Market Loop"),
            ]
            buses = []
            for index, (registration, model, seats, route_name) in enumerate(bus_specs):
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
                    VALUES (%s, %s, 'ACTIVE', %s, %s, %s, %s, %s)
                    RETURNING id, registration_number;
                    """,
                    (
                        registration,
                        route_ids[route_name],
                        acquired_date,
                        "Demo data only",
                        model,
                        seats,
                        f"DEMOCHASSIS{index + 1:03d}",
                    ),
                )
                bus = cursor.fetchone()
                buses.append(bus)
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
                    VALUES (%s, %s, 'PERMANENT', %s, 'ACTIVE', %s);
                    """,
                    (employment_ids[index], bus["id"], acquired_date, "Demo data only"),
                )

            account_openings = {
                "Cash": Decimal("2500.00"),
                "Airtel Money": Decimal("1500.00"),
                "Bank": Decimal("7500.00"),
            }
            account_ids = {}
            for name, opening_balance in account_openings.items():
                cursor.execute(
                    """
                    UPDATE financial_accounts
                    SET opening_balance = %s
                    WHERE name = %s
                    RETURNING id;
                    """,
                    (opening_balance, name),
                )
                account_ids[name] = cursor.fetchone()["id"]

            _insert_cashing_collection(
                cursor,
                previous_thursday,
                account_ids["Cash"],
                buses,
                normal_days=4,
                sunday_days=0,
                adjustments={},
            )
            _insert_cashing_collection(
                cursor,
                previous_sunday,
                account_ids["Airtel Money"],
                buses,
                normal_days=2,
                sunday_days=1,
                adjustments={"DEMO-103": Decimal("-150.00")},
            )
            _insert_cashing_collection(
                cursor,
                current_thursday,
                account_ids["Cash"],
                buses,
                normal_days=4,
                sunday_days=0,
                adjustments={"DEMO-102": Decimal("100.00")},
            )
            _insert_cashing_collection(
                cursor,
                last_sunday,
                account_ids["Airtel Money"],
                buses,
                normal_days=2,
                sunday_days=1,
                adjustments={"DEMO-104": Decimal("-300.00")},
            )

            categories = {
                name: _fetch_id(cursor, "expense_categories", "name", name)
                for name in [
                    "Maintenance",
                    "Parts",
                    "Driver Salaries",
                    "Transfer Fees",
                    "Office & Administration",
                    "Other",
                ]
            }
            bus_by_registration = {bus["registration_number"]: bus["id"] for bus in buses}
            expense_specs = [
                (
                    previous_thursday,
                    "Maintenance",
                    "Cash",
                    Decimal("850.00"),
                    "Brake adjustment",
                    "Demo Garage",
                    "DEMO-EXP-001",
                    "DEMO-101",
                ),
                (
                    previous_sunday - timedelta(days=2),
                    "Parts",
                    "Cash",
                    Decimal("420.00"),
                    "Replacement bulb set",
                    "Demo Parts Shop",
                    "DEMO-EXP-002",
                    "DEMO-102",
                ),
                (
                    previous_sunday,
                    "Transfer Fees",
                    "Airtel Money",
                    Decimal("25.00"),
                    "Mobile money transfer fee",
                    "Airtel Money",
                    "DEMO-EXP-003",
                    None,
                ),
                (
                    current_thursday - timedelta(days=4),
                    "Office & Administration",
                    "Bank",
                    Decimal("180.00"),
                    "Receipt books and stationery",
                    "Demo Stationers",
                    "DEMO-EXP-004",
                    None,
                ),
                (
                    current_thursday - timedelta(days=2),
                    "Maintenance",
                    "Cash",
                    Decimal("650.00"),
                    "Tyre puncture repairs",
                    "Demo Tyre Centre",
                    "DEMO-EXP-005",
                    "DEMO-103",
                ),
                (
                    current_thursday,
                    "Driver Salaries",
                    "Bank",
                    Decimal("2200.00"),
                    "Demo driver salary test entry",
                    "Demo Driver One",
                    "DEMO-EXP-006",
                    None,
                ),
                (
                    last_sunday - timedelta(days=1),
                    "Other",
                    "Cash",
                    Decimal("120.00"),
                    "Parking and loading fees",
                    "Demo Loading Bay",
                    "DEMO-EXP-007",
                    None,
                ),
                (
                    last_sunday,
                    "Transfer Fees",
                    "Airtel Money",
                    Decimal("35.00"),
                    "Sunday transfer fee",
                    "Airtel Money",
                    "DEMO-EXP-008",
                    None,
                ),
            ]
            for (
                expense_date,
                category_name,
                account_name,
                amount,
                description,
                vendor_name,
                reference_number,
                registration_number,
            ) in expense_specs:
                _insert_expense(
                    cursor,
                    expense_date,
                    categories[category_name],
                    account_ids[account_name],
                    amount,
                    description,
                    vendor_name,
                    reference_number,
                    bus_by_registration.get(registration_number) if registration_number else None,
                )

    print(
        "Seeded demo data: 4 buses, 4 drivers, 4 cashing collections, "
        "16 bus cashing rows, and 8 expenses."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="smartfleet_demo")
    args = parser.parse_args()
    seed_demo_database(args.database)


if __name__ == "__main__":
    main()
