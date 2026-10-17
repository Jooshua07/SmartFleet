"""Extend isolated local writer permissions for payroll and money workflows only."""

from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
MONEY_TABLES = (
    "driver_deductions",
    "driver_advances",
    "driver_salaries",
    "salary_advance_recoveries",
    "salary_deduction_allocations",
    "business_loans",
    "loan_repayments",
    "owner_loan_transactions",
)


def provision():
    for filename, name in (
        (".env.flask.local", "smartfleet_flask_dev"),
        (".env.flask.test.local", "smartfleet_flask_test"),
    ):
        env = dotenv_values(ROOT / filename)
        if (
            env.get("SMARTFLEET_DB_HOST") not in {"localhost", "127.0.0.1", "::1"}
            or env.get("SMARTFLEET_DB_NAME") != name
            or env.get("SMARTFLEET_FIXTURE_USER") != name + "_owner"
            or env.get("SMARTFLEET_WRITE_DB_USER") != name + "_writer"
        ):
            raise ValueError("Only the existing isolated loopback databases are accepted.")
        with psycopg.connect(
            host=env["SMARTFLEET_DB_HOST"],
            port=env["SMARTFLEET_DB_PORT"],
            dbname=name,
            user=env["SMARTFLEET_FIXTURE_USER"],
            password=env["SMARTFLEET_FIXTURE_PASSWORD"],
            connect_timeout=5,
        ) as connection:
            for table in MONEY_TABLES:
                connection.execute(
                    sql.SQL("GRANT INSERT,UPDATE,DELETE ON {} TO {}").format(
                        sql.Identifier(table), sql.Identifier(name + "_writer")
                    )
                )
            connection.execute(
                sql.SQL("GRANT INSERT ON correction_audit TO {}").format(
                    sql.Identifier(name + "_writer")
                )
            )
            # Existing integrity triggers lock the owner account; column-level UPDATE permits
            # that lock without authorizing changes to its identity/name/active flag.
            connection.execute(
                sql.SQL("GRANT UPDATE(notes) ON owner_loans TO {}").format(
                    sql.Identifier(name + "_writer")
                )
            )
            for category in ("Other", "Owner Drawings"):
                connection.execute(
                    "INSERT INTO expense_categories(name) VALUES (%s) ON CONFLICT(name) DO NOTHING",
                    (category,),
                )
        print("Prepared Stage 5 privileges:", name)


if __name__ == "__main__":
    provision()
