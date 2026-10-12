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


def main() -> None:
    temp_db = f"smartfleet_smart_cashing_smoke_{int(time.time())}"
    with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as admin_conn:
        with admin_conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(temp_db)))

    try:
        with psycopg.connect(**_connection_kwargs(temp_db)) as conn:
            with conn.cursor() as cursor:
                for migration in sorted(Path("migrations").glob("[0-9][0-9][0-9]_*.sql")):
                    cursor.execute(migration.read_text(encoding="utf-8"))

        os.environ["DB_NAME"] = temp_db

        from services.bus_service import create_bus
        from services.cashing_service import get_collection_destination_account
        from services.route_service import add_route
        from services.smart_cashing_service import (
            build_standard_allocations,
            get_smart_cashing_preview,
            record_smart_cashing_collection,
        )

        route = add_route("Smoke Route")
        bus = create_bus("SMK123", route["id"], date_acquired=date(2026, 10, 1))
        account = get_collection_destination_account()
        collection_date = date(2026, 10, 4)
        preview = get_smart_cashing_preview(collection_date)
        allocation = build_standard_allocations(preview, [bus["id"]], [], "1800")
        record_smart_cashing_collection(
            collection_date,
            account["id"],
            "1800",
            allocation["entries"],
            allocation["unallocated_amount"],
            allocation["difference_classification"],
        )

        with psycopg.connect(**_connection_kwargs(temp_db)) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
                    FROM remittance_collections;
                    """
                )
                collections = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM financial_transactions
                    WHERE transaction_type = 'CASHING';
                    """
                )
                ledger = cursor.fetchone()

        if collections != (1, 1800):
            raise RuntimeError(f"Unexpected collection result: {collections}")
        if ledger != (1, 1800):
            raise RuntimeError(f"Unexpected ledger result: {ledger}")

        print(f"Smart cashing smoke passed in {temp_db}.")
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

