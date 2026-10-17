from pathlib import Path

import psycopg
import pytest
from dotenv import dotenv_values
from psycopg import sql
from werkzeug.security import generate_password_hash

from smartfleet_web import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def isolated_config():
    path = ROOT / ".env.flask.test.local"
    if not path.is_file():
        pytest.fail("Required isolated local PostgreSQL test configuration is unavailable.")
    env = dotenv_values(path)
    assert env["SMARTFLEET_ENV"] == "testing"
    assert env["SMARTFLEET_DB_NAME"] == "smartfleet_flask_test"
    assert env["SMARTFLEET_DB_USER"] == "smartfleet_flask_test_reader"
    assert env["SMARTFLEET_DB_HOST"] in {"localhost", "127.0.0.1", "::1"}
    return {
        "TESTING": True,
        "SMARTFLEET_ENV": "testing",
        "SECRET_KEY": env["SMARTFLEET_SECRET_KEY"],
        "OWNER_USERNAME": "browser-owner",
        "OWNER_PASSWORD_HASH": generate_password_hash("browser-synthetic-passphrase"),
        "DB_SETTINGS": {
            "host": env["SMARTFLEET_DB_HOST"],
            "port": env["SMARTFLEET_DB_PORT"],
            "dbname": env["SMARTFLEET_DB_NAME"],
            "user": env["SMARTFLEET_DB_USER"],
            "password": env["SMARTFLEET_DB_PASSWORD"],
        },
        "TRUSTED_HOSTS": ["localhost", "127.0.0.1"],
    }


@pytest.fixture
def isolated_app(isolated_config):
    return create_app(isolated_config)


@pytest.fixture
def stage2_database(isolated_config):
    from smartfleet_web.management import TABLES, snapshot
    from smartfleet_web.recording import FINANCIAL_TABLES

    env = dotenv_values(ROOT / ".env.flask.test.local")
    assert env["SMARTFLEET_WRITE_DB_USER"] == "smartfleet_flask_test_writer"
    assert env["SMARTFLEET_FIXTURE_USER"] == "smartfleet_flask_test_owner"
    owner = {
        **isolated_config["DB_SETTINGS"],
        "user": env["SMARTFLEET_FIXTURE_USER"],
        "password": env["SMARTFLEET_FIXTURE_PASSWORD"],
    }
    writer = {
        **isolated_config["DB_SETTINGS"],
        "user": env["SMARTFLEET_WRITE_DB_USER"],
        "password": env["SMARTFLEET_WRITE_DB_PASSWORD"],
    }
    tables = list(
        dict.fromkeys(
            [
                *(table for group in TABLES.values() for table in group),
                *FINANCIAL_TABLES,
                "expense_categories",
            ]
        )
    )
    with psycopg.connect(**owner) as connection:
        before = snapshot(connection, tables)
        commands = set(connection.execute("SELECT actor,command_key FROM web_commands").fetchall())
    yield owner, writer
    # Restore only changes made to this isolated synthetic test fixture; never reset a database.
    order = [
        "cashing_obligation_payments",
        "cashing_obligations",
        "remittances",
        "remittance_collections",
        "expense_allocations",
        "expenses",
        "financial_transactions",
        "expense_categories",
        "bus_documents",
        "driver_assignments",
        "driver_salary_presets",
        "bus_route_history",
        "bus_status_history",
        "buses",
        "driver_employments",
        "drivers",
        "routes",
        "cashing_rates",
        "cashing_schedule_rules",
        "business_preset_audit",
        "reminder_presets",
        "business_settings",
        "financial_accounts",
    ]
    with psycopg.connect(**owner) as connection:
        current_commands = set(
            connection.execute("SELECT actor,command_key FROM web_commands").fetchall()
        )
        for actor, key in current_commands - commands:
            connection.execute(
                "DELETE FROM web_command_audit WHERE actor=%s AND command_key=%s", (actor, key)
            )
            connection.execute(
                "DELETE FROM web_commands WHERE actor=%s AND command_key=%s", (actor, key)
            )
        for table in order:
            key = (
                "setting_key"
                if table == "business_settings"
                else "preset_key"
                if table == "reminder_presets"
                else "id"
            )
            existing = [row[key] for row in before[table]]
            connection.execute(
                sql.SQL("DELETE FROM {} WHERE NOT ({} = ANY(%s))").format(
                    sql.Identifier(table), sql.Identifier(key)
                ),
                (existing,),
            )
        current = snapshot(connection, tables)
        for table in reversed(order):
            key = (
                "setting_key"
                if table == "business_settings"
                else "preset_key"
                if table == "reminder_presets"
                else "id"
            )
            for row in before[table]:
                if row in current[table]:
                    continue
                columns = [column for column in row if column != key]
                connection.execute(
                    sql.SQL("UPDATE {} SET {} WHERE {}=%s").format(
                        sql.Identifier(table),
                        sql.SQL(",").join(
                            sql.SQL("{}=%s").format(sql.Identifier(column)) for column in columns
                        ),
                        sql.Identifier(key),
                    ),
                    [*[row[column] for column in columns], row[key]],
                )


@pytest.fixture
def stage2_app(isolated_config, stage2_database):
    return create_app({**isolated_config, "WRITE_DB_SETTINGS": stage2_database[1]})


@pytest.fixture
def stage2_server(stage2_app):
    from threading import Thread

    from werkzeug.serving import make_server

    stage2_app.config.update(
        SESSION_COOKIE_SECURE=False, SESSION_COOKIE_NAME="smartfleet_loopback_session"
    )
    server = make_server("127.0.0.1", 0, stage2_app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()
