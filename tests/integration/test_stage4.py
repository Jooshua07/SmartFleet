from datetime import date

import psycopg
import pytest

from database.connection import shared_transaction
from services import (
    account_service,
    bus_account_service,
    cashing_service,
    driver_money_service,
    driver_service,
    expense_service,
    finance_service,
    loan_service,
)
from smartfleet_web.reporting import load_report
from tests.integration.test_stage2_workflows import BASE, login
from tests.integration.test_stage3 import identifiers

pytestmark = pytest.mark.integration


@pytest.fixture
def reporting_data(stage2_database):
    owner, _ = stage2_database
    account, category, buses = identifiers(owner)
    with shared_transaction(owner) as connection:
        cashing_service.record_direct_cashing_collection(
            date(2026, 10, 8),
            account,
            [{"include": True, "bus_id": b, "normal_amount": 1800} for b in buses],
        )
        expense_service.record_business_expense(
            date(2026, 10, 1), category, 4000, "Tyres", account, scope="BUS", bus_id=buses[0]
        )
        expense_service.record_business_expense(date(2026, 10, 2), category, 100, "Office", account)
        shared = expense_service.record_business_expense(
            date(2026, 10, 3), category, 600, "Shared parts", account
        )
        connection.execute("UPDATE expenses SET scope='MULTI_BUS' WHERE id=%s", (shared["id"],))
        for bus in buses:
            connection.execute(
                "INSERT INTO expense_allocations(expense_id,bus_id,allocated_amount) VALUES (%s,%s,300)",
                (shared["id"], bus),
            )
        driver = driver_service.create_driver(
            "Synthetic payroll driver", start_date=date(2026, 10, 1), monthly_salary=2000
        )
        employment = connection.execute(
            "SELECT id FROM driver_employments WHERE driver_id=%s", (driver["id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO driver_assignments(employment_id,bus_id,assignment_type,start_date) VALUES (%s,%s,'PERMANENT',DATE '2026-10-01')",
            (employment, buses[0]),
        )
        driver_money_service.record_driver_salary(
            employment,
            2026,
            10,
            date(2026, 10, 10),
            recovery_amount=0,
            financial_account_id=account,
        )
        loan_service.record_unidentified_business_loan_repayment(
            date(2026, 10, 11), 500, account, "Synthetic lender", "Unknown historical loan"
        )
        bank = connection.execute(
            "SELECT id FROM financial_accounts WHERE account_type='BANK'"
        ).fetchone()[0]
        transfer = connection.execute(
            "INSERT INTO transfers(transfer_date,source_account_id,destination_account_id,transfer_type,amount) VALUES (DATE '2026-10-12',%s,%s,'INTERNAL',1000) RETURNING id",
            (account, bank),
        ).fetchone()[0]
        for aid, direction in ((account, "OUT"), (bank, "IN")):
            connection.execute(
                "INSERT INTO financial_transactions(account_id,transaction_date,transaction_type,direction,amount,transfer_id) VALUES (%s,DATE '2026-10-12','TRANSFER',%s,1000,%s)",
                (aid, direction, transfer),
            )
        connection.execute(
            "UPDATE financial_accounts SET opening_balance=9000 WHERE id=%s", (account,)
        )
        for day, amount in ((date(2026, 11, 5), 3000), (date(2026, 12, 3), 5000)):
            cashing_service.record_direct_cashing_collection(
                day, account, [{"include": True, "bus_id": buses[0], "normal_amount": amount}]
            )
        for day, amount in ((date(2026, 11, 12), 500), (date(2026, 12, 10), 900)):
            expense_service.record_business_expense(
                day, category, amount, "Later expense", account, scope="BUS", bus_id=buses[0]
            )
    return {"owner": owner, "account": account, "category": category, "buses": buses}


def test_home_general_cards_asof_excludes_future_and_account_openings(
    stage2_app, reporting_data, monkeypatch
):
    monkeypatch.setattr("smartfleet_web.reporting.today_lusaka", lambda: date(2026, 10, 17))
    with stage2_app.app_context():
        data = load_report({}, "home")
    assert data["current"]["money_in"] == 3600
    assert data["current"]["money_out"] == 7200
    assert data["current"]["closing_balance"] == -3600
    assert data["series"][-1]["period_start"] == date(2026, 10, 17)
    assert data["series"][-1]["business_balance"] == -3600
    assert data["series"][-1]["total_expenses"] == data["current"]["money_out"] == 7200
    assert data["series"][-1]["operating_expenses"] == 6700
    red = data["chart_data"]["timeline"]["datasets"][1]
    assert red["label"] == "Total Expenses" and red["data"][-1] == 7200
    assert data["chart_data"]["bars"]["datasets"][1]["data"][0] == 6300
    client = login(stage2_app)
    response = client.get("/", base_url=BASE)
    assert response.status_code == 200
    assert b"Total Revenue" in response.data and b"Total Expenses" in response.data
    assert b'data-value="-3600.00"' in response.data


def test_october_november_december_and_three_month_period(stage2_app, reporting_data, monkeypatch):
    with shared_transaction(stage2_app.config["DB_SETTINGS"]):
        october = finance_service.get_period_balance(date(2026, 10, 1), date(2026, 10, 31))
        november = finance_service.get_period_balance(date(2026, 11, 1), date(2026, 11, 30))
        december = finance_service.get_period_balance(date(2026, 12, 1), date(2026, 12, 31))
    assert october["opening_balance"] == 0 and october["closing_balance"] == -3600
    assert november["opening_balance"] == -3600 and november["closing_balance"] == -1100
    assert december["opening_balance"] == -1100 and december["closing_balance"] == 3000
    monkeypatch.setattr("smartfleet_web.reporting.today_lusaka", lambda: date(2026, 12, 31))
    with stage2_app.app_context():
        data = load_report({"period": "3m", "view": "balances"}, "finance")
    assert data["start"] == date(2026, 10, 1)
    assert data["selected"]["money_in"] == 11600
    assert data["selected"]["money_out"] == 8600
    assert data["current"]["closing_balance"] == 3000


def test_bus_summary_detail_categories_salary_and_shared_reconcile(stage2_app, reporting_data):
    with shared_transaction(stage2_app.config["DB_SETTINGS"]):
        summary = bus_account_service.get_bus_contribution_summary(
            date(2026, 10, 1), date(2026, 10, 31)
        )
        assert summary["shared_general_costs"] == 100
        for bus in summary["buses"]:
            detail = bus_account_service.get_bus_account_detail(
                bus["bus_id"], date(2026, 10, 1), date(2026, 10, 31)
            )
            assert sum(r["recorded_revenue"] for r in detail["trend"]) == bus["recorded_revenue"]
            assert sum(r["attributed_costs"] for r in detail["trend"]) == bus["attributed_costs"]
            assert sum(r["amount"] for r in detail["costs_by_category"]) == bus["attributed_costs"]
            if bus["bus_id"] == reporting_data["buses"][0]:
                assert {r["category_name"]: r["amount"] for r in detail["costs_by_category"]} == {
                    "Maintenance": 4300,
                    "Driver Salaries": 2000,
                }


def test_account_balance_asof_keeps_opening_but_excludes_future(stage2_app, reporting_data):
    with shared_transaction(stage2_app.config["DB_SETTINGS"]):
        current = account_service.get_accounts_for_management(date(2026, 10, 17))
        all_dates = account_service.get_accounts_for_management()
    account_id = reporting_data["account"]
    current_account = next(row for row in current if row["id"] == account_id)
    all_dates_account = next(row for row in all_dates if row["id"] == account_id)
    assert current_account["opening_balance"] == 9000
    assert current_account["calculated_balance"] == 4400
    assert all_dates_account["calculated_balance"] == 11000
    assert all_dates_account["calculated_balance"] - current_account["calculated_balance"] == 6600


def test_total_expense_line_tracks_selected_dates_without_changing_balance(
    stage2_app, reporting_data, monkeypatch
):
    monkeypatch.setattr("smartfleet_web.reporting.today_lusaka", lambda: date(2026, 12, 31))
    cases = [
        ({"period": "1m"}, 900),
        ({"period": "3m"}, 8600),
        ({"period": "custom", "custom": "dates", "start": "2026-10-01", "end": "2026-10-10"}, 6700),
    ]
    with stage2_app.app_context():
        for args, expected in cases:
            data = load_report(args, "home")
            assert data["chart_data"]["timeline"]["datasets"][1]["data"][-1] == expected
            assert data["selected"]["money_out"] == expected
            assert data["current"]["closing_balance"] == 3000


@pytest.mark.parametrize(
    "path",
    [
        "/finance?view=general",
        "/finance?view=collections",
        "/finance?view=expenses",
        "/finance?view=balances",
        "/bus-accounts",
    ],
)
def test_report_pages_render_and_do_not_write(stage2_app, reporting_data, path):
    owner = reporting_data["owner"]
    with psycopg.connect(**owner) as connection:
        before = connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0]
    client = login(stage2_app)
    assert client.get(path, base_url=BASE).status_code == 200
    with psycopg.connect(**owner) as connection:
        assert (
            connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0]
            == before
        )
