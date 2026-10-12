from pathlib import Path
import os
import time

import psycopg
from dotenv import load_dotenv
from psycopg import sql


load_dotenv()


def _connection_kwargs(dbname: str) -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": dbname,
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


def main() -> None:
    temp_db = f"smartfleet_verify_{int(time.time())}"
    migrations = sorted(Path("migrations").glob("[0-9][0-9][0-9]_*.sql"))
    if not migrations:
        raise RuntimeError("No numbered migrations found.")

    with psycopg.connect(**_connection_kwargs("postgres"), autocommit=True) as admin_conn:
        with admin_conn.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(temp_db)))

    try:
        with psycopg.connect(**_connection_kwargs(temp_db)) as conn:
            with conn.cursor() as cursor:
                for migration in migrations:
                    cursor.execute(migration.read_text(encoding="utf-8"))
        print(f"Applied {len(migrations)} migrations to {temp_db}.")
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

