"""Grant recording permissions only on the two existing isolated Flask databases."""

from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]


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
            raise ValueError("Only the isolated local Flask targets are permitted.")
        with psycopg.connect(
            host=env["SMARTFLEET_DB_HOST"],
            port=env["SMARTFLEET_DB_PORT"],
            dbname=name,
            user=env["SMARTFLEET_FIXTURE_USER"],
            password=env["SMARTFLEET_FIXTURE_PASSWORD"],
            connect_timeout=5,
        ) as connection:
            for table in (
                "expenses",
                "expense_allocations",
                "financial_transactions",
                "remittance_collections",
                "remittances",
            ):
                connection.execute(
                    sql.SQL("GRANT INSERT,UPDATE,DELETE ON {} TO {}").format(
                        sql.Identifier(table), sql.Identifier(name + "_writer")
                    )
                )
            connection.execute(
                sql.SQL("GRANT INSERT,UPDATE ON cashing_obligations TO {}").format(
                    sql.Identifier(name + "_writer")
                )
            )
            connection.execute(
                sql.SQL("GRANT INSERT ON cashing_obligation_payments TO {}").format(
                    sql.Identifier(name + "_writer")
                )
            )
            for label in ("Fuel", "Maintenance", "Office & Administration"):
                connection.execute(
                    "INSERT INTO expense_categories(name) VALUES (%s) ON CONFLICT(name) DO NOTHING",
                    (label,),
                )
        print(f"Prepared Stage 3 recording privileges: {name}")


if __name__ == "__main__":
    provision()
