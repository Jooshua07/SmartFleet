import re

import psycopg
import pytest

from database.connection import get_connection, reset_connection_settings, set_connection_settings
from services.bus_service import get_all_buses

pytestmark = pytest.mark.integration


def test_connection_is_isolated_restricted_and_read_only(isolated_app):
    token = set_connection_settings(isolated_app.config["DB_SETTINGS"])
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT current_database(), current_user, current_setting('transaction_read_only'), "
                "rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=current_user"
            ).fetchone()
        assert row == (
            "smartfleet_flask_test",
            "smartfleet_flask_test_reader",
            "on",
            False,
            False,
            False,
            False,
        )
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction), get_connection() as conn:
            conn.execute("DELETE FROM buses WHERE false")
        with pytest.raises(psycopg.errors.InsufficientPrivilege), get_connection() as conn:
            conn.execute("SET TRANSACTION READ WRITE")
            conn.execute("DELETE FROM buses WHERE false")
    finally:
        reset_connection_settings(token)


def test_real_bus_query_and_filters(isolated_app):
    token = set_connection_settings(isolated_app.config["DB_SETTINGS"])
    try:
        rows = get_all_buses(limit=21)
        assert {row["registration_number"] for row in rows} == {
            "DEMO101",
            "DEMO102",
            "DEMO103",
            "DEMO104",
        }
        assert len(get_all_buses(limit=21, status="ACTIVE")) == 3
        assert get_all_buses(limit=21, search="DEMO102")[0]["registration_number"] == "DEMO102"
        assert get_all_buses(limit=21, search="' OR 1=1 --") == []
        assert len(get_all_buses(limit=2, offset=2)) == 2
    finally:
        reset_connection_settings(token)


def test_schema_integrity_objects_are_present(isolated_app):
    token = set_connection_settings(isolated_app.config["DB_SETTINGS"])
    try:
        with get_connection() as conn:
            tables = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
            ).fetchone()[0]
            functions = conn.execute(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'sf_%'"
            ).fetchone()[0]
            triggers = conn.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgenabled='O'"
            ).fetchone()[0]
        assert tables == 39
        assert functions == 20
        assert triggers == 51
    finally:
        reset_connection_settings(token)


def test_route_uses_real_isolated_database(isolated_app):
    client = isolated_app.test_client()
    page = client.get("/login", base_url="https://localhost")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()
    response = client.post(
        "/login",
        base_url="https://localhost",
        headers={"Referer": "https://localhost/login"},
        data={
            "csrf_token": token,
            "username": "browser-owner",
            "password": "browser-synthetic-passphrase",
        },
    )
    assert response.status_code == 303
    assert b"DEMO101" in client.get("/buses", base_url="https://localhost").data
    assert client.get("/health/ready", base_url="https://localhost").json == {"status": "ready"}
