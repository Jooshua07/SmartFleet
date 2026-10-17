"""Grant only the isolated servicing writes and backup sequence reads."""

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
            or env.get("SMARTFLEET_DB_USER") != name + "_reader"
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
            for table in ("maintenance", "maintenance_schedules"):
                connection.execute(
                    sql.SQL("GRANT INSERT,UPDATE ON {} TO {}").format(
                        sql.Identifier(table), sql.Identifier(name + "_writer")
                    )
                )
            connection.execute(
                sql.SQL("GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(
                    sql.Identifier(name + "_reader")
                )
            )
            connection.execute(
                "INSERT INTO expense_categories(name) VALUES ('Servicing') ON CONFLICT(name) DO NOTHING"
            )
        print("Prepared Stage 6 privileges:", name)


if __name__ == "__main__":
    provision()
