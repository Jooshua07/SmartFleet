"""Add command safety and a least-privilege writer ONLY in isolated local Flask databases."""

import secrets
import sys
from pathlib import Path

import psycopg
from dotenv import dotenv_values, set_key
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def provision():
    from scripts.setup_flask_dev import local_admin_settings

    source = local_admin_settings()
    admin = {
        "host": source["DB_HOST"],
        "port": source["DB_PORT"],
        "dbname": "postgres",
        "user": source["DB_USER"],
        "password": source["DB_PASSWORD"],
        "connect_timeout": 5,
    }
    for filename, name in (
        (".env.flask.local", "smartfleet_flask_dev"),
        (".env.flask.test.local", "smartfleet_flask_test"),
    ):
        path = ROOT / filename
        env = dotenv_values(path)
        if (
            env.get("SMARTFLEET_DB_HOST") not in {"127.0.0.1", "localhost", "::1"}
            or env.get("SMARTFLEET_DB_NAME") != name
            or env.get("SMARTFLEET_FIXTURE_USER") != name + "_owner"
        ):
            raise ValueError("Refusing anything except the isolated local target.")
        writer = name + "_writer"
        password = env.get("SMARTFLEET_WRITE_DB_PASSWORD") or secrets.token_urlsafe(32)
        with psycopg.connect(**admin) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (writer,)
            ).fetchone()
            if exists and not env.get("SMARTFLEET_WRITE_DB_PASSWORD"):
                raise ValueError(
                    "Existing writer without local credentials; inspect partial setup."
                )
            if not exists:
                connection.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                        "NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(writer), sql.Literal(password))
                )
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(name), sql.Identifier(writer)
                )
            )
        owner = {
            "host": env["SMARTFLEET_DB_HOST"],
            "port": env["SMARTFLEET_DB_PORT"],
            "dbname": name,
            "user": env["SMARTFLEET_FIXTURE_USER"],
            "password": env["SMARTFLEET_FIXTURE_PASSWORD"],
            "connect_timeout": 5,
        }
        with psycopg.connect(**owner) as connection:
            if (
                connection.execute("SELECT to_regclass('public.web_commands')").fetchone()[0]
                is None
            ):
                connection.execute((ROOT / "migrations/flask/001_command_safety.sql").read_text())
            connection.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(writer))
            )
            connection.execute(
                sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}, {}").format(
                    sql.Identifier(writer), sql.Identifier(name + "_reader")
                )
            )
            tables = [
                "buses",
                "bus_status_history",
                "bus_route_history",
                "bus_documents",
                "routes",
                "drivers",
                "driver_employments",
                "driver_assignments",
                "business_settings",
                "business_preset_audit",
                "cashing_rates",
                "cashing_schedule_rules",
                "driver_salary_presets",
                "reminder_presets",
                "financial_accounts",
            ]
            for table in tables:
                connection.execute(
                    sql.SQL("GRANT INSERT,UPDATE ON {} TO {}").format(
                        sql.Identifier(table), sql.Identifier(writer)
                    )
                )
            connection.execute(
                sql.SQL("GRANT INSERT ON web_commands,web_command_audit TO {}").format(
                    sql.Identifier(writer)
                )
            )
            connection.execute(
                sql.SQL("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {}").format(
                    sql.Identifier(writer)
                )
            )
            # Schema-only Stage 1 clones intentionally had no configuration/history rows.
            connection.execute("""
                INSERT INTO bus_status_history(bus_id,status,effective_from,reason)
                SELECT b.id,b.status,DATE '2026-10-01','Synthetic fixture history' FROM buses b
                WHERE NOT EXISTS (SELECT 1 FROM bus_status_history h WHERE h.bus_id=b.id)
            """)
            connection.execute("""
                INSERT INTO bus_route_history(bus_id,route_id,effective_from,notes)
                SELECT b.id,b.route_id,DATE '2026-10-01','Synthetic fixture history' FROM buses b
                WHERE NOT EXISTS (SELECT 1 FROM bus_route_history h WHERE h.bus_id=b.id)
            """)
            for day, covered, sunday in ((4, [1, 2, 3], True), (7, [4, 5, 6], False)):
                connection.execute(
                    """
                    INSERT INTO cashing_schedule_rules(collection_day,covered_days,include_previous_sunday,effective_from,notes)
                    SELECT %s,%s,%s,DATE '2026-10-01','Synthetic default'
                    WHERE NOT EXISTS(SELECT 1 FROM cashing_schedule_rules WHERE collection_day=%s)
                """,
                    (day, covered, sunday, day),
                )
            for rate_type, amount in (("NORMAL_DAY", 600), ("SUNDAY", 300)):
                connection.execute(
                    """INSERT INTO cashing_rates(rate_type,amount,effective_from)
                    SELECT %s,%s,DATE '2026-10-01' WHERE NOT EXISTS(
                        SELECT 1 FROM cashing_rates WHERE rate_type=%s)
                """,
                    (rate_type, amount, rate_type),
                )
            for account_type, label in (
                ("CASH", "Cash"),
                ("AIRTEL_MONEY", "Airtel Money"),
                ("BANK", "Bank"),
            ):
                connection.execute(
                    """INSERT INTO financial_accounts(name,account_type,opening_balance)
                    SELECT %s,%s,0 WHERE NOT EXISTS(SELECT 1 FROM financial_accounts WHERE account_type=%s)
                """,
                    (label, account_type, account_type),
                )
        set_key(path, "SMARTFLEET_WRITE_DB_USER", writer)
        set_key(path, "SMARTFLEET_WRITE_DB_PASSWORD", password)
        print(f"Prepared isolated Stage 2 database: {name}")


if __name__ == "__main__":
    provision()
