import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import psycopg
import pytest

from database.connection import get_connection, shared_transaction
from services import driver_service, expense_service
from smartfleet_web import money
from tests.integration.test_stage2_workflows import BASE, form, login, post
from tests.integration.test_stage3 import cash_form, identifiers

pytestmark = pytest.mark.integration


@pytest.fixture
def money_data(stage2_database):
    owner, _ = stage2_database
    with shared_transaction(owner) as connection:
        driver = driver_service.create_driver(
            "Synthetic Payroll Driver", start_date=date(2026, 10, 1), monthly_salary=2000
        )
        employment = connection.execute(
            "SELECT id FROM driver_employments WHERE driver_id=%s", (driver["id"],)
        ).fetchone()[0]
        connection.execute("INSERT INTO owner_loans(name) VALUES ('Synthetic Owner')")
    return {"owner": owner, "employment": employment}


def values(client, action, **data):
    return {
        **form(client, "/money/" + action),
        "date": "2026-10-10",
        "notes": "Synthetic history",
        "reason": "Synthetic entry",
        **data,
    }


def save(client, action, **data):
    response = post(client, "/money/" + action, values(client, action, **data))
    assert response.status_code == 303, response.data.decode()[:600]
    return response


def scalar(owner, query, params=()):
    with psycopg.connect(**owner) as connection:
        return connection.execute(query, params).fetchone()[0]


def reverse(client, kind, record_id):
    path = f"/money/cancel/{kind}/{record_id}"
    data = {**form(client, path), "confirm": "on", "reason": "Correct mistaken entry"}
    response = post(client, path, data)
    assert response.status_code == 303, response.data.decode()[:600]
    assert post(client, path, data).status_code == 303


def test_advance_salary_fifo_replay_preview_and_cancellation(stage2_app, money_data):
    owner, employment = money_data["owner"], str(money_data["employment"])
    client = login(stage2_app)
    advance = values(client, "advance", employment_id=employment, amount="300")
    assert post(client, "/money/advance", advance).status_code == 303
    assert post(client, "/money/advance", advance).status_code == 303
    save(client, "advance", employment_id=employment, amount="200")
    salary = values(
        client,
        "salary",
        employment_id=employment,
        salary_year="2026",
        salary_month="10",
        recovery_amount="400",
        other_deductions="0",
    )
    assert post(client, "/money/salary", {**salary, "intent": "preview"}).status_code == 200
    assert scalar(owner, "SELECT count(*) FROM driver_salaries") == 0
    assert post(client, "/money/salary", salary).status_code == 303
    assert post(client, "/money/salary", salary).status_code == 303
    assert scalar(owner, "SELECT net_salary FROM driver_salaries") == 1600
    with psycopg.connect(**owner) as connection:
        recoveries = connection.execute(
            "SELECT amount FROM salary_advance_recoveries ORDER BY advance_id"
        ).fetchall()
        assert recoveries == [(Decimal(300),), (Decimal(100),)]
        assert (
            connection.execute(
                "SELECT sum(amount) FROM financial_transactions WHERE direction='OUT'"
            ).fetchone()[0]
            == 2100
        )
        salary_id = connection.execute("SELECT id FROM driver_salaries").fetchone()[0]
        advance_id = connection.execute("SELECT min(id) FROM driver_advances").fetchone()[0]
    path = f"/money/cancel/advance/{advance_id}"
    assert (
        post(
            client, path, {**form(client, path), "confirm": "on", "reason": "Wrong advance"}
        ).status_code
        == 400
    )
    reverse(client, "salary", salary_id)
    assert scalar(owner, "SELECT count(*) FROM salary_advance_recoveries") == 0
    assert scalar(owner, "SELECT count(*) FROM driver_advances WHERE status='ACTIVE'") == 2
    reverse(client, "advance", advance_id)
    assert scalar(owner, "SELECT count(*) FROM correction_audit") == 2
    with psycopg.connect(**owner) as connection:
        audits = connection.execute(
            "SELECT actor,reason,before_state,after_state FROM web_command_audit"
        ).fetchall()
        assert len(audits) == 5 and all(
            r[0] == "browser-owner" and r[1] and r[2] != r[3] for r in audits
        )
    assert (
        b'name="amount" type="number" value=""' in client.get("/money/advance", base_url=BASE).data
    )


@pytest.mark.parametrize("amount", ["", "0", "-1", "NaN", "1.001", "1001"])
def test_invalid_advance_has_no_financial_effect(stage2_app, money_data, amount):
    client = login(stage2_app)
    response = post(
        client,
        "/money/advance",
        values(client, "advance", employment_id=str(money_data["employment"]), amount=amount),
    )
    assert response.status_code == 400
    assert scalar(money_data["owner"], "SELECT count(*) FROM financial_transactions") == 0
    assert scalar(money_data["owner"], "SELECT count(*) FROM web_commands") == 0


def test_salary_zero_net_duplicate_month_and_over_recovery(stage2_app, money_data):
    client = login(stage2_app)
    data = dict(
        employment_id=str(money_data["employment"]),
        salary_year="2026",
        salary_month="10",
        recovery_amount="1",
        other_deductions="0",
    )
    assert post(client, "/money/salary", values(client, "salary", **data)).status_code == 400
    save(client, "salary", **{**data, "recovery_amount": "0", "other_deductions": "2000"})
    assert scalar(money_data["owner"], "SELECT count(*) FROM financial_transactions") == 0
    assert scalar(money_data["owner"], "SELECT net_salary FROM driver_salaries") == 0
    assert (
        scalar(money_data["owner"], "SELECT sum(amount) FROM salary_deduction_allocations") == 2000
    )
    assert (
        post(
            client, "/money/salary", values(client, "salary", **{**data, "recovery_amount": "0"})
        ).status_code
        == 409
    )
    salary_id = scalar(money_data["owner"], "SELECT id FROM driver_salaries")
    reverse(client, "salary", salary_id)
    assert scalar(money_data["owner"], "SELECT count(*) FROM salary_deduction_allocations") == 0
    assert scalar(money_data["owner"], "SELECT count(*) FROM driver_deductions WHERE applied") == 0


def test_loans_personal_funds_fees_association_and_reversals(stage2_app, money_data):
    owner = money_data["owner"]
    client = login(stage2_app)
    save(
        client,
        "loan",
        loan_name="Synthetic loan",
        lender="Synthetic association",
        original_amount="1000",
        default_monthly_repayment="100",
        term_months="10",
    )
    loan = scalar(owner, "SELECT id FROM business_loans")
    assert scalar(owner, "SELECT count(*) FROM financial_transactions") == 0
    save(
        client,
        "repayment",
        loan_id="",
        payment_source="BUSINESS_ACCOUNT",
        principal_amount="200",
        interest_or_fees="20",
        paid_to="Association",
        reference="R1",
    )
    repayment = scalar(owner, "SELECT id FROM loan_repayments")
    before = scalar(owner, "SELECT sum(amount) FROM financial_transactions")
    save(client, "associate", loan_id=str(loan), repayment_id=str(repayment))
    assert scalar(owner, "SELECT sum(amount) FROM financial_transactions") == before
    assert scalar(owner, "SELECT loan_id FROM loan_repayments") == loan
    save(
        client,
        "owner-pays-loan",
        loan_id=str(loan),
        principal_amount="300",
        interest_or_fees="30",
        paid_to="Association",
        reference="P1",
    )
    assert scalar(owner, "SELECT sum(amount) FROM financial_transactions") == before
    assert scalar(owner, "SELECT sum(amount) FROM owner_loan_transactions") == 330
    personal_id = scalar(
        owner, "SELECT id FROM loan_repayments WHERE payment_source='OWNER_PERSONAL'"
    )
    assert (
        post(
            client,
            "/money/repayment",
            values(
                client,
                "repayment",
                loan_id=str(loan),
                payment_source="BUSINESS_ACCOUNT",
                principal_amount="501",
                interest_or_fees="0",
                paid_to="",
                reference="",
            ),
        ).status_code
        == 400
    )
    reverse(client, "repayment", personal_id)
    # The existing schema stores finance charges separately, without a repayment FK.
    # Reversing principal must not guess and erase a potentially unrelated fee.
    assert scalar(owner, "SELECT sum(amount) FROM owner_loan_transactions") == 30
    reverse(client, "repayment", repayment)
    assert scalar(owner, "SELECT sum(amount) FROM financial_transactions") == 20


def test_owner_funding_drawing_repayment_caps_and_cancellation(stage2_app, money_data):
    client, owner = login(stage2_app), money_data["owner"]
    save(client, "owner-funding", amount="1000")
    save(client, "owner-drawing", amount="100", reference="DRAW")
    assert (
        post(
            client, "/money/owner-repayment", values(client, "owner-repayment", amount="1001")
        ).status_code
        == 400
    )
    save(client, "owner-repayment", amount="400")
    assert (
        scalar(
            owner,
            "SELECT sum(CASE WHEN transaction_type='OWNER_FUNDED' THEN amount ELSE -amount END) FROM owner_loan_transactions",
        )
        == 600
    )
    drawing = scalar(owner, "SELECT id FROM expenses")
    reverse(client, "drawing", drawing)
    repayment = scalar(
        owner, "SELECT id FROM owner_loan_transactions WHERE transaction_type='REPAYMENT'"
    )
    reverse(client, "owner", repayment)
    funding = scalar(owner, "SELECT id FROM owner_loan_transactions")
    reverse(client, "owner", funding)
    assert scalar(owner, "SELECT count(*) FROM financial_transactions") == 0


@pytest.mark.parametrize("action", ["reclassify-salary", "reclassify-loan"])
def test_historical_reclassification_preserves_one_payment(stage2_app, money_data, action):
    owner = money_data["owner"]
    account, category, _ = identifiers(owner)
    with shared_transaction(owner):
        expense_service.record_business_expense(
            date(2026, 10, 3), category, 500, "Historical payment", account, scope="GENERAL"
        )
    expense_id = scalar(owner, "SELECT id FROM expenses")
    client = login(stage2_app)
    data = dict(
        expense_id=str(expense_id),
        employment_id=str(money_data["employment"]),
        salary_year="2026",
        salary_month="10",
        loan_id="",
    )
    save(client, action, **data)
    assert scalar(owner, "SELECT count(*) FROM expenses") == 0
    assert scalar(owner, "SELECT count(*) FROM financial_transactions") == 1
    assert scalar(owner, "SELECT amount FROM financial_transactions") == 500


def test_money_retry_concurrency_stale_form_and_audit_failure(stage2_app, money_data):
    owner = money_data["owner"]
    a, b = login(stage2_app), login(stage2_app)
    data = values(a, "advance", employment_id=str(money_data["employment"]), amount="100")
    stale = values(b, "advance", employment_id=str(money_data["employment"]), amount="200")
    other_token = form(b, "/money/advance")["csrf_token"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [
            pool.submit(post, a, "/money/advance", data),
            pool.submit(post, b, "/money/advance", {**data, "csrf_token": other_token}),
        ]
        assert [task.result().status_code for task in tasks] == [303, 303]
    assert post(b, "/money/advance", stale).status_code == 409
    bad = values(
        a,
        "advance",
        employment_id=str(money_data["employment"]),
        amount="200",
        reason="Invalid audit\x00",
    )
    assert post(a, "/money/advance", bad).status_code == 409
    assert scalar(owner, "SELECT count(*) FROM driver_advances") == 1
    assert scalar(owner, "SELECT count(*) FROM web_command_audit") == 1


def test_money_deferred_failure_rolls_back_everything(stage2_app, money_data, monkeypatch):
    original = money.payroll.record_driver_advance

    def inconsistent(*args, **kwargs):
        row = original(*args, **kwargs)
        with get_connection() as connection:
            connection.execute(
                "UPDATE financial_transactions SET amount=amount+1 WHERE id=%s",
                (row["financial_transaction_id"],),
            )
        return row

    monkeypatch.setattr(money.payroll, "record_driver_advance", inconsistent)
    client = login(stage2_app)
    assert (
        post(
            client,
            "/money/advance",
            values(client, "advance", employment_id=str(money_data["employment"]), amount="100"),
        ).status_code
        == 503
    )
    for table in ("driver_advances", "financial_transactions", "web_commands", "web_command_audit"):
        assert (
            scalar(
                money_data["owner"],
                psycopg.sql.SQL("SELECT count(*) FROM {}").format(psycopg.sql.Identifier(table)),
            )
            == 0
        )


@pytest.mark.parametrize(
    "path", ["/driver-money", "/loans", "/owner-money", *["/money/" + a for a in money.ACTIONS]]
)
def test_money_pages_render(stage2_app, money_data, path):
    assert login(stage2_app).get(path, base_url=BASE).status_code == 200


def test_money_replay_after_actual_process_restart(stage2_app, money_data):
    client = login(stage2_app)
    data = values(client, "advance", employment_id=str(money_data["employment"]), amount="100")
    assert post(client, "/money/advance", data).status_code == 303
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
c=login(app);v=json.loads(sys.stdin.read())
v['csrf_token']=form(c,'/money/advance')['csrf_token']
assert post(c,'/money/advance',v).status_code==303
print('Restart replay passed')
"""
    result = subprocess.run(  # noqa: S603 -- fixed interpreter/code and synthetic stdin only.
        [sys.executable, "-c", code],
        input=json.dumps(data),
        text=True,
        capture_output=True,
        timeout=90,
        check=True,
    )
    assert "Restart replay passed" in result.stdout
    assert scalar(money_data["owner"], "SELECT count(*) FROM financial_transactions") == 1


def test_automatic_airtel_and_bus_scope_are_server_authoritative(stage2_app, stage2_database):
    owner, _ = stage2_database
    account, category, buses = identifiers(owner)
    client = login(stage2_app)
    data = {
        **form(client, "/record-expense"),
        "expense_date": "2026-10-01",
        "category_id": str(category),
        "scope": "GENERAL",
        "bus_id": str(buses[0]),
        "financial_account_id": "999999",
        "amount": "100",
        "description": "Auto account",
        "reason": "Synthetic",
    }
    assert post(client, "/record-expense", data).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT bus_id,financial_account_id FROM expenses"
        ).fetchone() == (None, account)
    data.update(form(client, "/record-expense"), scope="BUS", bus_id="")
    assert post(client, "/record-expense", data).status_code == 400
    assert scalar(owner, "SELECT count(*) FROM expenses") == 1
    cash = cash_form(client, owner)
    cash["financial_account_id"] = "999999"
    assert post(client, "/record-cashing", cash).status_code == 303
    assert scalar(owner, "SELECT financial_account_id FROM remittance_collections") == account


def test_partial_employment_preview_and_outside_advance_date(stage2_app, money_data):
    owner, employment = money_data["owner"], money_data["employment"]
    with psycopg.connect(**owner) as connection:
        connection.execute(
            "UPDATE driver_employments SET start_date=DATE '2026-10-16' WHERE id=%s", (employment,)
        )
    client = login(stage2_app)
    payload = values(
        client,
        "salary",
        employment_id=str(employment),
        salary_year="2026",
        salary_month="10",
        other_deductions="0",
        recovery_amount="",
    )
    preview = post(client, "/money/salary", {**payload, "intent": "preview"})
    assert preview.status_code == 200 and b"1032.26" in preview.data
    invalid = values(
        client, "advance", employment_id=str(employment), amount="100", date="2026-10-01"
    )
    assert post(client, "/money/advance", invalid).status_code == 400
    assert scalar(owner, "SELECT count(*) FROM financial_transactions") == 0


def test_two_competing_repayments_do_not_overpay(stage2_app, money_data):
    owner = money_data["owner"]
    a, b = login(stage2_app), login(stage2_app)
    save(
        a,
        "loan",
        loan_name="Concurrent loan",
        lender="Association",
        original_amount="1000",
        default_monthly_repayment="",
        term_months="",
    )
    loan = scalar(owner, "SELECT id FROM business_loans")
    detail = dict(
        loan_id=str(loan),
        payment_source="BUSINESS_ACCOUNT",
        principal_amount="600",
        interest_or_fees="0",
        paid_to="",
        reference="",
    )
    first, second = values(a, "repayment", **detail), values(b, "repayment", **detail)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(post, a, "/money/repayment", first),
            pool.submit(post, b, "/money/repayment", second),
        ]
        assert sorted(task.result().status_code for task in futures) == [303, 409]
    assert scalar(owner, "SELECT sum(amount) FROM loan_repayments") == 600
