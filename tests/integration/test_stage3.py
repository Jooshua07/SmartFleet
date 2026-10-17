import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import psycopg
import pytest

from database.connection import shared_transaction
from services import bus_service, cashing_service
from tests.integration.test_stage2_workflows import BASE, form, login, post

pytestmark = pytest.mark.integration


def identifiers(owner):
    with psycopg.connect(**owner) as connection:
        account = connection.execute(
            "SELECT id FROM financial_accounts WHERE account_type='AIRTEL_MONEY'"
        ).fetchone()[0]
        category = connection.execute(
            "SELECT id FROM expense_categories WHERE name='Maintenance'"
        ).fetchone()[0]
        buses = [
            r[0]
            for r in connection.execute(
                "SELECT id FROM buses WHERE status='ACTIVE' ORDER BY id LIMIT 2"
            )
        ]
    return account, category, buses


def cash_form(client, owner, mode="STANDARD", ids=None, day="2026-10-08"):
    account, _, buses = identifiers(owner)
    ids = ids or buses[:1]
    values = {
        **form(client, "/record-cashing?date=" + day),
        "collection_date": day,
        "financial_account_id": str(account),
        "bus_ids": [str(b) for b in ids],
        "mode": mode,
        "total_received": str(1800 * len(ids)),
        "reason": "Synthetic collection",
        "classification": "UNKNOWN_DIFFERENCE",
    }
    for bus in ids:
        values.update(
            {f"amount_{bus}": "1800", f"days_{bus}": "3", f"classification_{bus}": "MATCHED"}
        )
    return values


def test_expense_create_replay_correct_delete_and_blank_form(stage2_app, stage2_database):
    owner, _ = stage2_database
    account, category, _ = identifiers(owner)
    client = login(stage2_app)
    values = {
        **form(client, "/record-expense"),
        "expense_date": "2026-10-01",
        "category_id": str(category),
        "financial_account_id": str(account),
        "amount": "4000",
        "scope": "GENERAL",
        "description": "Tyre purchase",
        "vendor_name": "Synthetic shop",
        "reference_number": "TEST-REF",
        "reason": "Synthetic expense",
    }
    assert post(client, "/record-expense", values).status_code == 303
    assert post(client, "/record-expense", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        expense = connection.execute("SELECT id,financial_transaction_id FROM expenses").fetchone()
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 1
    path = f"/expenses/{expense[0]}/edit"
    values.update(form(client, path))
    values.update(amount="3900", reason="Correct receipt")
    assert post(client, path, values).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert (
            connection.execute(
                "SELECT amount FROM financial_transactions WHERE id=%s", (expense[1],)
            ).fetchone()[0]
            == 3900
        )
    path = f"/delete/expense/{expense[0]}"
    deletion = {**form(client, path), "reason": "Cancel mistaken entry", "confirm": "on"}
    assert post(client, path, deletion).status_code == 303
    assert post(client, path, deletion).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM expenses").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM web_command_audit").fetchone()[0] == 3
    assert (
        b'name="amount" type="number" value=""' in client.get("/record-expense", base_url=BASE).data
    )


@pytest.mark.parametrize(
    "mode,count,sunday",
    [("STANDARD", 1, False), ("STANDARD", 2, False), ("ADJUSTED", 1, False), ("ADJUSTED", 2, True)],
)
def test_one_multiple_buses_sunday_and_clearing(stage2_app, stage2_database, mode, count, sunday):
    owner, _ = stage2_database
    client = login(stage2_app)
    _, _, buses = identifiers(owner)
    values = cash_form(client, owner, mode, buses[:count])
    if sunday:
        for bid in buses[:count]:
            values.update({f"sunday_{bid}": "on", f"sunday_amount_{bid}": "300"})
    response = post(client, "/record-cashing", values)
    assert response.status_code == 303, response.data.decode()
    assert post(client, "/record-cashing", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT count(*),sum(actual_amount) FROM remittances"
        ).fetchone() == (count, count * (2100 if sunday else 1800))
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 1
    page = client.get("/record-cashing?date=2026-10-08", base_url=BASE)
    bus_select = re.search(rb'<select id="bus_ids".*?</select>', page.data, re.S)[0]
    assert b" selected" not in bus_select
    assert b'name="total_received" type="number" min="0" step="0.01" value=""' in page.data


@pytest.mark.parametrize(
    "change",
    [
        "missing_bus",
        "missing_amount",
        "nan",
        "scale",
        "invalid_bus",
        "excess_days",
        "missing_reason",
        "wrong_weekday",
        "future",
    ],
)
def test_invalid_cashing_rolls_back_and_retains_draft(stage2_app, stage2_database, change):
    owner, _ = stage2_database
    client = login(stage2_app)
    values = cash_form(client, owner, "ADJUSTED")
    bid = values["bus_ids"][0]
    if change == "missing_bus":
        values["bus_ids"] = []
    elif change == "missing_amount":
        values[f"amount_{bid}"] = ""
    elif change == "nan":
        values[f"amount_{bid}"] = "NaN"
    elif change == "scale":
        values[f"amount_{bid}"] = "1.001"
    elif change == "invalid_bus":
        values["bus_ids"] = ["999999"]
    elif change == "excess_days":
        values[f"days_{bid}"] = "4"
    elif change == "missing_reason":
        values["reason"] = ""
    elif change == "wrong_weekday":
        values["collection_date"] = "2026-10-05"
    else:
        values["collection_date"] = "2099-10-08"
    response = post(client, "/record-cashing", values)
    assert response.status_code == 400, response.data.decode()
    assert b'role="alert"' in response.data
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM web_commands").fetchone()[0] == 0


def test_shortfall_obligation_partial_full_overpayment_and_correction_lock(
    stage2_app, stage2_database
):
    owner, _ = stage2_database
    client = login(stage2_app)
    values = cash_form(client, owner, "ADJUSTED")
    bid = values["bus_ids"][0]
    values.update(
        {
            f"amount_{bid}": "1000",
            f"classification_{bid}": "CONFIRMED_UNPAID_OBLIGATION",
            f"explanation_{bid}": "Driver owes the balance",
            f"responsible_{bid}": "Synthetic driver",
        }
    )
    assert post(client, "/record-cashing", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        obligation = connection.execute(
            "SELECT id,collection_id FROM cashing_obligations"
        ).fetchone()
    path = f"/obligations/{obligation[0]}"
    account, _, _ = identifiers(owner)
    payment = {
        **form(client, path),
        "payment_date": "2026-10-09",
        "financial_account_id": str(account),
        "amount": "300",
        "reason": "Part payment",
    }
    assert post(client, path, payment).status_code == 303
    assert post(client, path, payment).status_code == 303
    payment.update(form(client, path))
    payment["amount"] = "501"
    assert post(client, path, payment).status_code == 400
    payment["amount"] = "500"
    assert post(client, path, payment).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT outstanding_amount,status FROM cashing_obligations"
        ).fetchone() == (0, "SETTLED")
        assert (
            connection.execute(
                "SELECT sum(amount) FROM financial_transactions WHERE transaction_type='OTHER' AND direction='IN'"
            ).fetchone()[0]
            == 800
        )
    delete = f"/delete/collection/{obligation[1]}"
    assert (
        post(
            client,
            delete,
            {**form(client, delete), "confirm": "on", "reason": "Blocked correction"},
        ).status_code
        == 400
    )


def test_smart_correction_zero_receipt_and_deletion(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    values = cash_form(client, owner)
    assert post(client, "/record-cashing", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        cid = connection.execute("SELECT id FROM remittance_collections").fetchone()[0]
    path = f"/collections/{cid}/edit"
    values.update(form(client, path))
    values.update(total_received="0", reason="No receipt yet")
    assert post(client, path, values).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0
        assert (
            connection.execute("SELECT unallocated_amount FROM remittance_collections").fetchone()[
                0
            ]
            == -1800
        )
    path = f"/delete/collection/{cid}"
    assert (
        post(
            client, path, {**form(client, path), "confirm": "on", "reason": "Cancel test"}
        ).status_code
        == 303
    )


def test_concurrent_same_financial_command_is_one_receipt(stage2_app, stage2_database):
    owner, _ = stage2_database
    clients = [login(stage2_app), login(stage2_app)]
    values = [cash_form(c, owner) for c in clients]
    values[1]["command_token"] = values[0]["command_token"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda i: post(clients[i], "/record-cashing", values[i]).status_code, range(2))
        )
    assert results == [303, 303]
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM remittance_collections").fetchone()[0] == 1


def test_new_collection_day_and_sunday_only_historical_bus(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    path = "/presets/schedule"
    schedule = {
        **form(client, path),
        "enabled_2": "on",
        "covered_2": ["1"],
        "enabled_4": "on",
        "covered_4": ["2", "3"],
        "sunday_4": "on",
        "enabled_7": "on",
        "covered_7": ["4", "5", "6"],
        "effective_from": "2026-10-05",
        "reason": "Historical schedule",
    }
    assert post(client, path, schedule).status_code == 303
    values = cash_form(client, owner, day="2026-10-06")
    values["total_received"] = "600"
    response = post(client, "/record-cashing", values)
    assert response.status_code == 303, response.data.decode()
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT coverage_start,coverage_end,total_amount FROM remittance_collections"
        ).fetchone() == (date(2026, 10, 5), date(2026, 10, 5), 600)


def test_sunday_only_activation_and_inactive_normal_days(stage2_app, stage2_database):
    owner, _ = stage2_database
    with shared_transaction(owner) as connection:
        route = connection.execute("SELECT id FROM routes LIMIT 1").fetchone()[0]
        bus = bus_service.create_bus("SUNDAY-TEST", route, date_acquired=date(2026, 10, 4))
        bus_service.set_bus_status(bus["id"], "INACTIVE", date(2026, 10, 5), "Sunday only")
    client = login(stage2_app)
    values = cash_form(client, owner, ids=[bus["id"]])
    values.update(
        {"total_received": "300", f"sunday_{bus['id']}": "on", f"sunday_amount_{bus['id']}": "300"}
    )
    response = post(client, "/record-cashing", values)
    assert response.status_code == 303, response.data.decode()
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT normal_days,sunday_days,actual_amount FROM remittances"
        ).fetchone() == (0, 1, 300)


def test_direct_historical_correction_and_delete(stage2_app, stage2_database):
    owner, _ = stage2_database
    account, _, buses = identifiers(owner)
    with shared_transaction(owner):
        collection = cashing_service.record_direct_cashing_collection(
            date(2026, 10, 2),
            account,
            [{"include": True, "bus_id": buses[0], "normal_amount": "500"}],
        )
    client = login(stage2_app)
    path = f"/collections/{collection['id']}/edit"
    values = {
        **form(client, path),
        "collection_date": "2026-10-02",
        "financial_account_id": str(account),
        "bus_ids": [str(buses[0])],
        "mode": "DIRECT",
        f"amount_{buses[0]}": "550",
        "reason": "Historical correction",
    }
    assert post(client, path, values).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT amount FROM financial_transactions").fetchone()[0] == 550
    path = f"/delete/collection/{collection['id']}"
    assert (
        post(
            client, path, {**form(client, path), "confirm": "on", "reason": "Cancel direct"}
        ).status_code
        == 303
    )


def test_financial_replay_after_process_restart(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    values = cash_form(client, owner)
    assert post(client, "/record-cashing", values).status_code == 303
    code = """
import json,sys
from dotenv import dotenv_values
from werkzeug.security import generate_password_hash
from smartfleet_web import create_app
from tests.integration.test_stage2_workflows import login,form,post
e=dotenv_values('.env.flask.test.local')
assert e['SMARTFLEET_DB_NAME']=='smartfleet_flask_test'
db=dict(host=e['SMARTFLEET_DB_HOST'],port=e['SMARTFLEET_DB_PORT'],dbname=e['SMARTFLEET_DB_NAME'],user=e['SMARTFLEET_DB_USER'],password=e['SMARTFLEET_DB_PASSWORD'])
writer={**db,'user':e['SMARTFLEET_WRITE_DB_USER'],'password':e['SMARTFLEET_WRITE_DB_PASSWORD']}
app=create_app(dict(TESTING=True,SMARTFLEET_ENV='testing',SECRET_KEY=e['SMARTFLEET_SECRET_KEY'],OWNER_USERNAME='browser-owner',OWNER_PASSWORD_HASH=generate_password_hash('browser-synthetic-passphrase'),DB_SETTINGS=db,WRITE_DB_SETTINGS=writer,TRUSTED_HOSTS=['localhost']))
c=login(app)
v=json.loads(sys.stdin.read())
v['csrf_token']=form(c,'/record-cashing?date=2026-10-08')['csrf_token']
assert post(c,'/record-cashing',v).status_code==303
print('Replay passed')
"""
    result = subprocess.run(  # noqa: S603 -- fixed interpreter/code; synthetic payload on stdin.
        [sys.executable, "-c", code],
        input=json.dumps(values),
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )  # noqa: S603 -- fixed synthetic test interpreter/code.
    assert "Replay passed" in result.stdout
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 1


@pytest.mark.parametrize(
    "received,unallocated,classification",
    [("1500", -300, "UNKNOWN_DIFFERENCE"), ("2000", 200, "SURPLUS")],
)
def test_standard_signed_difference_preserves_actual_receipt(
    stage2_app, stage2_database, received, unallocated, classification
):
    owner, _ = stage2_database
    client = login(stage2_app)
    values = cash_form(client, owner)
    values["total_received"] = received
    assert post(client, "/record-cashing", values).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT unallocated_amount,difference_classification FROM remittance_collections"
        ).fetchone() == (unallocated, classification)
        assert (
            str(connection.execute("SELECT amount FROM financial_transactions").fetchone()[0])
            == received + ".00"
        )


def test_cash_receipt_and_audit_rollback_on_commit_failure(
    stage2_app, stage2_database, monkeypatch
):
    from database.connection import get_connection
    from smartfleet_web import recording

    owner, _ = stage2_database
    client = login(stage2_app)
    original = recording.cashing.record_smart_cashing_collection

    def inconsistent(*args, **kwargs):
        result = original(*args, **kwargs)
        with get_connection() as connection:
            connection.execute(
                "UPDATE financial_transactions SET amount=amount+1 WHERE id=(SELECT financial_transaction_id FROM remittance_collections WHERE id=%s)",
                (result["id"],),
            )
        return result

    monkeypatch.setattr(recording.cashing, "record_smart_cashing_collection", inconsistent)
    response = post(client, "/record-cashing", cash_form(client, owner))
    assert response.status_code == 503
    with psycopg.connect(**owner) as connection:
        for table in (
            "financial_transactions",
            "remittance_collections",
            "remittances",
            "web_commands",
            "web_command_audit",
        ):
            assert (
                connection.execute(
                    psycopg.sql.SQL("SELECT count(*) FROM {}").format(psycopg.sql.Identifier(table))
                ).fetchone()[0]
                == 0
            )


def test_financial_audit_insert_failure_rolls_back_receipt(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    values = cash_form(client, owner)
    values["reason"] = "Invalid audit text\x00"
    assert post(client, "/record-cashing", values).status_code == 409
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM web_commands").fetchone()[0] == 0
