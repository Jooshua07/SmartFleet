from datetime import date
from decimal import Decimal

import psycopg
import pytest

from database.connection import shared_transaction
from services import bus_service, preset_service
from tests.integration.test_stage2_workflows import BASE, form, login, post
from tests.integration.test_stage3 import identifiers

pytestmark = pytest.mark.integration


def payload(client, mode="STANDARD", **changes):
    return {
        **form(client, "/record-cashing?date=2026-10-08"),
        "collection_date": "2026-10-08",
        "mode": mode,
        "notes": "Synthetic invoice",
        **changes,
    }


def rows(owner):
    with psycopg.connect(**owner) as connection:
        return connection.execute(
            "SELECT b.registration_number,r.actual_amount FROM remittances r JOIN buses b ON b.id=r.bus_id ORDER BY b.registration_number"
        ).fetchall()


def adjustment(bid, amount, classification="UNKNOWN_DIFFERENCE", explanation="Actual receipt"):
    return {
        f"amount_{bid}": amount,
        f"classification_{bid}": classification,
        f"explanation_{bid}": explanation,
    }


def test_standard_all_eligible_server_total_and_receipt(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    data = payload(
        client, bus_ids=["1"], total_received="1", financial_account_id="999999", amount_1="1"
    )
    response = post(client, "/record-cashing", data)
    assert response.status_code == 303
    assert response.location.endswith("/receipt")
    assert rows(owner) == [
        ("DEMO101", Decimal(1800)),
        ("DEMO102", Decimal(1800)),
        ("DEMO104", Decimal(1800)),
    ]
    assert post(client, "/record-cashing", data).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute(
            "SELECT count(*),sum(amount) FROM financial_transactions"
        ).fetchone() == (1, 5400)
        assert connection.execute(
            "SELECT total_amount,expected_total,unallocated_amount FROM remittance_collections"
        ).fetchone() == (5400, 5400, 0)
        assert (
            connection.execute(
                "SELECT account_type FROM financial_accounts WHERE id=(SELECT financial_account_id FROM remittance_collections)"
            ).fetchone()[0]
            == "AIRTEL_MONEY"
        )
    receipt = client.get(response.location, base_url=BASE)
    assert receipt.status_code == 200 and b"5,400.00" in receipt.data and b"DEMO104" in receipt.data


@pytest.mark.parametrize("count", [1, 2, 3])
def test_only_explicit_adjustments_and_unedited_standards(stage2_app, stage2_database, count):
    owner, _ = stage2_database
    with psycopg.connect(**owner) as connection:
        buses = [
            r[0]
            for r in connection.execute("SELECT id FROM buses WHERE status='ACTIVE' ORDER BY id")
        ]
    client = login(stage2_app)
    data = payload(client, "ADJUSTED", adjust_ids=[str(b) for b in buses[:count]])
    for bid in buses:
        # Forged unselected amounts must not change standard entries.
        data.update(adjustment(bid, "1000"))
    assert post(client, "/record-cashing", data).status_code == 303
    assert [r[1] for r in rows(owner)] == [1000] * count + [1800] * (3 - count)


@pytest.mark.parametrize(
    "amount", ["", "NaN", "Infinity", "-1", "1.001", "not-money", "1000000000"]
)
def test_blank_invalid_adjustments_no_partial_writes(stage2_app, stage2_database, amount):
    owner, _ = stage2_database
    bid = identifiers(owner)[2][0]
    client = login(stage2_app)
    data = payload(client, "ADJUSTED", adjust_ids=[str(bid)], **adjustment(bid, amount))
    response = post(client, "/record-cashing", data)
    assert response.status_code == 400
    assert rows(owner) == []
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM web_commands").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0


def test_explicit_zero_all_buses_no_ledger_but_obligations(stage2_app, stage2_database):
    owner, _ = stage2_database
    with psycopg.connect(**owner) as connection:
        buses = [
            r[0]
            for r in connection.execute("SELECT id FROM buses WHERE status='ACTIVE' ORDER BY id")
        ]
    client = login(stage2_app)
    data = payload(client, "ADJUSTED", adjust_ids=[str(b) for b in buses])
    for bid in buses:
        data.update(adjustment(bid, "0", "CONFIRMED_UNPAID_OBLIGATION"))
        data[f"responsible_{bid}"] = "Synthetic person"
    assert post(client, "/record-cashing", data).status_code == 303
    with psycopg.connect(**owner) as connection:
        assert connection.execute("SELECT count(*) FROM financial_transactions").fetchone()[0] == 0
        assert connection.execute(
            "SELECT count(*),sum(outstanding_amount) FROM cashing_obligations"
        ).fetchone() == (3, 5400)
        assert connection.execute(
            "SELECT total_amount,financial_transaction_id FROM remittance_collections"
        ).fetchone() == (0, None)
    assert [r[1] for r in rows(owner)] == [0, 0, 0]


@pytest.mark.parametrize(
    "classification,explanation,responsible",
    [
        ("MATCHED", "Actual", ""),
        ("SURPLUS", "Actual", ""),
        ("UNKNOWN_DIFFERENCE", "", ""),
        ("CONFIRMED_UNPAID_OBLIGATION", "Actual", ""),
    ],
)
def test_shortage_classification_explanation_responsibility_required(
    stage2_app, stage2_database, classification, explanation, responsible
):
    owner, _ = stage2_database
    bid = identifiers(owner)[2][0]
    client = login(stage2_app)
    data = payload(
        client,
        "ADJUSTED",
        adjust_ids=[str(bid)],
        **adjustment(bid, "1000", classification, explanation),
    )
    data[f"responsible_{bid}"] = responsible
    assert post(client, "/record-cashing", data).status_code == 400
    assert rows(owner) == []


def test_surplus_and_reduced_worked_days(stage2_app, stage2_database):
    owner, _ = stage2_database
    buses = identifiers(owner)[2]
    client = login(stage2_app)
    data = payload(client, "ADJUSTED", adjust_ids=[str(b) for b in buses])
    data.update(adjustment(buses[0], "2000", "SURPLUS"))
    data.update(adjustment(buses[1], "1200", "REDUCED_WORKDAYS", "Bus worked two days"))
    data[f"days_{buses[1]}"] = "2"
    assert post(client, "/record-cashing", data).status_code == 303
    assert [r[1] for r in rows(owner)] == [2000, 1200, 1800]


def test_date_bound_token_and_changed_rates_need_reload(stage2_app, stage2_database):
    owner, _ = stage2_database
    client = login(stage2_app)
    data = payload(client)
    data["collection_date"] = "2026-10-11"
    assert post(client, "/record-cashing", data).status_code == 409
    assert rows(owner) == []
    data = payload(client)
    with shared_transaction(owner):
        preset_service.set_cashing_rate(
            "NORMAL_DAY", 700, date(2026, 10, 8), "Reviewed synthetic rate"
        )
    assert post(client, "/record-cashing", data).status_code == 409
    assert rows(owner) == []
    assert post(client, "/record-cashing", payload(client)).status_code == 303
    assert [r[1] for r in rows(owner)] == [2100, 2100, 2100]


def test_no_eligible_buses_disabled_and_post_rejected(stage2_app, stage2_database):
    owner, _ = stage2_database
    with psycopg.connect(**owner) as connection:
        connection.execute("UPDATE bus_status_history SET status='INACTIVE'")
    client = login(stage2_app)
    page = client.get("/record-cashing?date=2026-10-08", base_url=BASE)
    assert b"No eligible buses" in page.data and b'disabled><i data-lucide="save"' in page.data
    assert post(client, "/record-cashing", payload(client)).status_code == 400
    assert rows(owner) == []


def test_historical_partial_activity_and_no_future_activation(stage2_app, stage2_database):
    owner, _ = stage2_database
    with shared_transaction(owner) as connection:
        route = connection.execute("SELECT id FROM routes LIMIT 1").fetchone()[0]
        bus_service.create_bus("PARTIAL-TEST", route, date_acquired=date(2026, 10, 7))
        bus_service.create_bus("LATER-TEST", route, date_acquired=date(2026, 10, 9))
    client = login(stage2_app)
    assert post(client, "/record-cashing", payload(client)).status_code == 303
    actual = dict(rows(owner))
    assert actual["PARTIAL-TEST"] == 600
    assert "LATER-TEST" not in actual and "DEMO103" not in actual


def test_adjustment_reset_ignores_abandoned_fields(stage2_app, stage2_database):
    owner, _ = stage2_database
    bid = identifiers(owner)[2][0]
    client = login(stage2_app)
    assert (
        post(
            client,
            "/record-cashing",
            payload(client, "ADJUSTED", adjust_ids=[], **adjustment(bid, "0")),
        ).status_code
        == 303
    )
    assert [r[1] for r in rows(owner)] == [1800, 1800, 1800]


def test_single_eligible_bus_full_receipt(stage2_app, stage2_database):
    owner, _ = stage2_database
    bid = identifiers(owner)[2][0]
    with psycopg.connect(**owner) as connection:
        connection.execute(
            "UPDATE bus_status_history SET status='INACTIVE' WHERE bus_id<>%s", (bid,)
        )
    client = login(stage2_app)
    assert post(client, "/record-cashing", payload(client)).status_code == 303
    assert rows(owner) == [("DEMO101", Decimal(1800))]


def test_scientific_notation_uses_same_actual_amount_as_preview(stage2_app, stage2_database):
    owner, _ = stage2_database
    bid = identifiers(owner)[2][0]
    client = login(stage2_app)
    data = payload(client, "ADJUSTED", adjust_ids=[str(bid)], **adjustment(bid, "1e3"))
    assert post(client, "/record-cashing", data).status_code == 303
    assert [r[1] for r in rows(owner)] == [1000, 1800, 1800]
