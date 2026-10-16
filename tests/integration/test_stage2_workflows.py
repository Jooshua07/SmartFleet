import re
from datetime import date
from uuid import uuid4

import psycopg
import pytest

from database.connection import reset_connection_settings, set_connection_settings
from services.collection_schedule_service import coverage_from_rules
from services.smart_cashing_service import get_smart_cashing_preview

pytestmark = pytest.mark.integration
BASE = "https://localhost"


def hidden(response, name):
    return re.search(f'name="{name}" value="([^"]+)"'.encode(), response.data)[1].decode()


def login(app):
    client = app.test_client()
    response = client.get("/login", base_url=BASE)
    assert (
        client.post(
            "/login",
            base_url=BASE,
            headers={"Referer": BASE + "/login"},
            data={
                "csrf_token": hidden(response, "csrf_token"),
                "username": "browser-owner",
                "password": "browser-synthetic-passphrase",
            },
        ).status_code
        == 303
    )
    return client


def form(client, path):
    response = client.get(path, base_url=BASE)
    assert response.status_code == 200
    return {name: hidden(response, name) for name in ("csrf_token", "command_token")}


def post(client, path, values):
    return client.post(path, base_url=BASE, headers={"Referer": BASE + path}, data=values)


def test_driver_bus_history_status_and_repeated_submit(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    driver_name = "TEST-Driver-" + uuid4().hex[:8]
    values = {
        **form(client, "/manage/driver-new"),
        "full_name": driver_name,
        "start_date": "2026-10-01",
        "monthly_salary": "2000",
        "reason": "Synthetic driver setup",
    }
    assert post(client, "/manage/driver-new", values).status_code == 303
    assert post(client, "/manage/driver-new", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        employment = connection.execute(
            "SELECT e.id FROM drivers d JOIN driver_employments e ON e.driver_id=d.id WHERE d.full_name=%s",
            (driver_name,),
        ).fetchone()[0]
        route = connection.execute("SELECT id FROM routes WHERE active LIMIT 1").fetchone()[0]
    registration = "T" + uuid4().hex[:8].upper()
    values = {
        **form(client, "/manage/bus-new"),
        "registration_number": registration,
        "route_id": str(route),
        "employment_id": str(employment),
        "date_acquired": "2026-10-01",
        "status": "ACTIVE",
        "seating_capacity": "26",
        "doc_INSURANCE_number": "SYNTHETIC-POLICY",
        "doc_INSURANCE_issue": "2026-10-01",
        "doc_INSURANCE_expiry": "2027-10-01",
        "reason": "Synthetic bus setup",
    }
    assert post(client, "/manage/bus-new", values).status_code == 303
    assert post(client, "/manage/bus-new", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        bus_id = connection.execute(
            "SELECT id FROM buses WHERE registration_number=%s", (registration,)
        ).fetchone()[0]
        assert (
            connection.execute(
                "SELECT count(*) FROM driver_assignments WHERE bus_id=%s", (bus_id,)
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute(
                "SELECT document_number FROM bus_documents WHERE bus_id=%s", (bus_id,)
            ).fetchone()[0]
            == "SYNTHETIC-POLICY"
        )
    path = f"/manage/bus-status/{bus_id}"
    values = {
        **form(client, path),
        "status": "INACTIVE",
        "effective_date": "2026-10-10",
        "reason": "Synthetic repair period",
    }
    assert post(client, path, values).status_code == 303
    assert b"Synthetic repair period" in client.get(f"/buses/{bus_id}", base_url=BASE).data
    with psycopg.connect(**owner) as connection:
        history = connection.execute(
            "SELECT status,effective_from,effective_to FROM bus_status_history WHERE bus_id=%s ORDER BY effective_from",
            (bus_id,),
        ).fetchall()
        assert history == [
            ("ACTIVE", date(2026, 10, 1), date(2026, 10, 9)),
            ("INACTIVE", date(2026, 10, 10), None),
        ]
    token = set_connection_settings(stage2_app.config["DB_SETTINGS"])
    try:
        preview = get_smart_cashing_preview(
            date(2026, 10, 11),
            schedule_rules=[
                {
                    "collection_day": 7,
                    "covered_days": [4, 5, 6],
                    "include_previous_sunday": False,
                    "effective_from": date(2026, 10, 1),
                    "effective_to": None,
                }
            ],
        )
        bus = next(row for row in preview["buses"] if row["id"] == bus_id)
        assert bus["normal_days"] == 2
        assert bus["expected_amount"] == 1200
    finally:
        reset_connection_settings(token)


@pytest.mark.parametrize("amount", ["", "NaN", "Infinity", "-1", "1.001", "oops"])
def test_bad_account_input_keeps_values_and_changes_nothing(stage2_app, stage2_database, amount):
    owner, _ = stage2_database
    client = login(stage2_app)
    with psycopg.connect(**owner) as connection:
        account = connection.execute("SELECT id FROM financial_accounts LIMIT 1").fetchone()[0]
    path = f"/manage/account/{account}"
    response = post(
        client,
        path,
        {**form(client, path), "opening_balance": amount, "reason": "Synthetic invalid input"},
    )
    assert response.status_code == 400
    assert b"Synthetic invalid input" in response.data
    with psycopg.connect(**owner) as connection:
        assert (
            connection.execute(
                "SELECT opening_balance FROM financial_accounts WHERE id=%s", (account,)
            ).fetchone()[0]
            == 0
        )


def test_account_money_stale_edit_csrf_and_missing_command(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    with psycopg.connect(**owner) as connection:
        account = connection.execute("SELECT id FROM financial_accounts LIMIT 1").fetchone()[0]
    path = f"/manage/account/{account}"
    first, second = form(client, path), form(client, path)
    assert (
        post(
            client, path, {**first, "opening_balance": "4000.25", "reason": "Synthetic opening"}
        ).status_code
        == 303
    )
    assert (
        post(
            client, path, {**second, "opening_balance": "8000", "reason": "Stale edit"}
        ).status_code
        == 409
    )
    fresh = form(client, path)
    assert (
        post(
            client,
            path,
            {"csrf_token": fresh["csrf_token"], "opening_balance": "5", "reason": "Missing key"},
        ).status_code
        == 409
    )
    assert post(client, path, {"opening_balance": "5"}).status_code == 400
    with psycopg.connect(**owner) as connection:
        assert (
            str(
                connection.execute(
                    "SELECT opening_balance FROM financial_accounts WHERE id=%s", (account,)
                ).fetchone()[0]
            )
            == "4000.25"
        )


def test_schedule_add_day_retains_history_and_rejects_overlap(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    path = "/presets/schedule"
    data = {
        **form(client, path),
        "enabled_2": "on",
        "covered_2": ["1"],
        "enabled_4": "on",
        "covered_4": ["2", "3"],
        "sunday_4": "on",
        "enabled_7": "on",
        "covered_7": ["4", "5", "6"],
        "effective_from": "2026-10-19",
        "reason": "Synthetic three-day schedule",
    }
    response = post(client, path, data)
    assert response.status_code == 303, response.data.decode()
    assert post(client, path, data).status_code == 303
    with psycopg.connect(**owner, row_factory=psycopg.rows.dict_row) as connection:
        rules = connection.execute("SELECT * FROM cashing_schedule_rules").fetchall()
        assert len(rules) == 5
        assert coverage_from_rules(date(2026, 10, 8), rules)["coverage_start"] == date(2026, 10, 5)
        assert coverage_from_rules(date(2026, 10, 20), rules)["coverage_start"] == date(
            2026, 10, 19
        )
    assert (
        client.get("/presets/schedule/coverage?date=2026-10-20", base_url=BASE).json[
            "collection_type"
        ]
        == "TUESDAY"
    )
    data.update(form(client, path))
    data.update(covered_4=["1", "2", "3"], effective_from="2026-10-26")
    assert post(client, path, data).status_code == 400


@pytest.mark.parametrize(
    "kind,fields,table",
    [
        (
            "rate",
            {"rate_type": "NORMAL_DAY", "amount": "650.25", "effective_from": "2026-10-20"},
            "cashing_rates",
        ),
        (
            "salary",
            {"driver_id": "", "monthly_salary": "2100.50", "effective_from": "2026-10-20"},
            "driver_salary_presets",
        ),
        ("advance", {"amount": "900.25"}, "business_settings"),
        (
            "reminder",
            {"preset_key": "DOCUMENT_EXPIRY_WARNING_DAYS", "warning_days": "14", "active": "on"},
            "reminder_presets",
        ),
        ("reporting", {"baseline_date": "2026-10-01"}, "business_settings"),
    ],
)
def test_each_preset_saves_once_with_owner_audit(stage2_app, stage2_database, kind, fields, table):
    owner, _ = stage2_database
    client = login(stage2_app)
    path = f"/manage/{kind}"
    values = {**form(client, path), **fields, "reason": "Synthetic preset", "actor": "forged-owner"}
    assert post(client, path, values).status_code == 303
    assert post(client, path, values).status_code == 303
    with psycopg.connect(**owner) as connection:
        audit = connection.execute(
            "SELECT actor,after_state FROM web_command_audit ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert audit[0] == "browser-owner"
        assert audit[1][table]
        assert (
            connection.execute(
                "SELECT count(*) FROM web_commands WHERE action=%s", (kind + ":0",)
            ).fetchone()[0]
            == 1
        )


def test_route_duplicate_and_new_form_clears(stage2_app, stage2_database):
    client = login(stage2_app)
    path = "/manage/route-new"
    name = "TEST-" + uuid4().hex
    values = {
        **form(client, path),
        "name": name,
        "description": "Synthetic route",
        "reason": "Initial route",
    }
    assert post(client, path, values).status_code == 303
    page = client.get(path, base_url=BASE)
    assert b'id="name" name="name" type="text" value=""' in page.data
    values.update(form(client, path))
    assert post(client, path, values).status_code == 409
    values.update(name="", reason="Blank route")
    assert post(client, path, values).status_code == 400


@pytest.mark.parametrize(
    "field,value",
    [
        ("seating_capacity", "0"),
        ("seating_capacity", "2.5"),
        ("route_id", "999999"),
        ("registration_number", "X" * 21),
        ("reason", ""),
    ],
)
def test_invalid_bus_form_commits_nothing(stage2_app, stage2_database, field, value):
    owner, _ = stage2_database
    client = login(stage2_app)
    path = "/manage/bus-new"
    with psycopg.connect(**owner) as connection:
        route = connection.execute("SELECT id FROM routes LIMIT 1").fetchone()[0]
    values = {
        **form(client, path),
        "registration_number": "TEST-INVALID",
        "route_id": str(route),
        "status": "ACTIVE",
        "date_acquired": "2026-10-01",
        "reason": "Synthetic invalid bus",
        field: value,
    }
    assert post(client, path, values).status_code == 400
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM buses").fetchone()[0] == 4


def test_schedule_rejects_transition_that_repeats_work(stage2_app, stage2_database):
    client = login(stage2_app)
    path = "/presets/schedule"
    data = {
        **form(client, path),
        "enabled_5": "on",
        "covered_5": ["1", "2", "3"],
        "sunday_5": "on",
        "enabled_7": "on",
        "covered_7": ["4", "5", "6"],
        "effective_from": "2026-10-16",
        "reason": "Ambiguous transition",
    }
    response = post(client, path, data)
    assert response.status_code == 400
    assert b"transition skips or repeats" in response.data
