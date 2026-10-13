from datetime import date
from pathlib import Path
import os
import sys
import time

import psycopg
from dotenv import load_dotenv
from psycopg import sql


load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _connection_kwargs(dbname: str) -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": dbname,
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


def _category_id(name: str) -> int:
    with psycopg.connect(**_connection_kwargs(os.environ["DB_NAME"])) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM expense_categories WHERE name = %s;", (name,))
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"Missing category {name}")
            return row[0]


def main() -> None:
    temp_db = f"smartfleet_expense_finance_smoke_{int(time.time())}"
    with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as admin_conn:
        with admin_conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(temp_db)))

    try:
        with psycopg.connect(**_connection_kwargs(temp_db)) as conn:
            with conn.cursor() as cursor:
                for migration in sorted(Path("migrations").glob("[0-9][0-9][0-9]_*.sql")):
                    cursor.execute(migration.read_text(encoding="utf-8"))

        os.environ["DB_NAME"] = temp_db

        from services.bus_account_service import get_bus_contribution_summary
        from services.bus_service import create_bus
        from services.expense_service import record_business_expense
        from services.finance_service import get_business_balance
        from services.loan_service import record_unidentified_business_loan_repayment
        from services.route_service import add_route

        route = add_route("Smoke Route")
        aih = create_bus("AIH123", route["id"], date_acquired=date(2026, 10, 1))
        aif = create_bus("AIF123", route["id"], date_acquired=date(2026, 10, 1))

        parts_id = _category_id("Parts")
        maintenance_id = _category_id("Maintenance")

        record_business_expense(date(2026, 10, 2), maintenance_id, 4000, "AIH bushes", scope="BUS", bus_id=aih["id"])
        record_business_expense(date(2026, 10, 3), parts_id, 4000, "AIH tyres", scope="BUS", bus_id=aih["id"])
        record_business_expense(date(2026, 10, 4), parts_id, 3000, "Brake pads", notes="10 brake pads")
        record_business_expense(date(2026, 10, 5), parts_id, 2000, "Air filters", notes="Four air filters")
        record_business_expense(date(2026, 10, 6), parts_id, 2535, "Oil filters", notes="Seven oil filters")
        record_unidentified_business_loan_repayment(
            date(2026, 10, 7),
            15000,
            2,
            "Business lender",
            "October clean-slate loan principal repayment",
        )

        summary = get_bus_contribution_summary(date(2026, 10, 1), date(2026, 10, 31))
        balance = get_business_balance()

        aih_summary = next(row for row in summary["buses"] if row["bus_id"] == aih["id"])
        aif_summary = next(row for row in summary["buses"] if row["bus_id"] == aif["id"])

        if aih_summary["attributed_costs"] != 8000:
            raise RuntimeError(f"AIH costs should be 8000, got {aih_summary['attributed_costs']}")
        if aif_summary["attributed_costs"] != 0:
            raise RuntimeError(f"AIF costs should be 0, got {aif_summary['attributed_costs']}")
        if summary["shared_general_costs"] != 7535:
            raise RuntimeError(f"Shared costs should be 7535, got {summary['shared_general_costs']}")
        if balance["business_balance"] != -30535:
            raise RuntimeError(f"Business Balance should be -30535, got {balance['business_balance']}")
        if balance["operating_payments"] != 15535:
            raise RuntimeError(f"Operating payments should be 15535, got {balance['operating_payments']}")
        if balance["financing_out"] != 15000:
            raise RuntimeError(f"Financing out should be 15000, got {balance['financing_out']}")

        print(f"Expense and finance smoke passed in {temp_db}.")
    finally:
        with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as admin_conn:
            with admin_conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid();
                    """,
                    (temp_db,),
                )
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(temp_db)))


if __name__ == "__main__":
    main()
