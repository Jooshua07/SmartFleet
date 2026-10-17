from datetime import date
from decimal import Decimal

import pytest

from smartfleet_web.reporting import bar_data, choose_period, with_total_expenses


@pytest.mark.parametrize(
    "args,start",
    [
        ({"period": "1m"}, date(2026, 12, 1)),
        ({"period": "3m"}, date(2026, 10, 1)),
        ({"period": "custom", "custom": "6m"}, date(2026, 10, 1)),
        ({"period": "custom", "custom": "all"}, date(2026, 10, 4)),
    ],
)
def test_calendar_periods_and_earliest_record(args, start):
    assert choose_period(args, date(2026, 10, 1), date(2026, 12, 17), date(2026, 10, 4)) == (
        start,
        date(2026, 12, 17),
    )


@pytest.mark.parametrize(
    "args",
    [
        {"period": "bad"},
        {"period": "custom", "custom": "bad"},
        {"period": "custom", "custom": "dates"},
        {"period": "custom", "custom": "dates", "start": "2026-12-31", "end": "2026-10-01"},
        {"period": "custom", "custom": "dates", "start": "2000-01-01", "end": "2026-10-01"},
    ],
)
def test_bad_period_inputs(args):
    with pytest.raises(ValueError):
        choose_period(args, date(2026, 10, 1), date(2026, 12, 17))


def test_bar_amounts_are_actual_currency_not_cents():
    data = bar_data(
        [
            {
                "name": "ABC123",
                "recorded_revenue": Decimal("1800"),
                "attributed_costs": Decimal("4000"),
            }
        ],
        "name",
    )
    assert data["datasets"][1]["data"] == [4000]


def test_all_time_with_only_future_records_does_not_reverse_the_period():
    assert choose_period(
        {"period": "custom", "custom": "all"},
        date(2026, 10, 1),
        date(2026, 10, 17),
        date(2026, 11, 5),
    ) == (date(2026, 10, 1), date(2026, 10, 17))


@pytest.mark.parametrize(
    "kind", ["EXPENSE", "DRIVER_SALARY", "LOAN_REPAYMENT", "OWNER_DRAWING", "TRANSFER_FEE", "OTHER"]
)
def test_total_expense_line_includes_every_outgoing_payment(kind):
    series = [{"period_start": date(2026, 10, 4)}, {"period_start": date(2026, 10, 8)}]
    ledger = [
        {
            "transaction_date": date(2026, 10, 1),
            "transaction_type": kind,
            "direction": "OUT",
            "amount": Decimal("4000.25"),
        },
        {
            "transaction_date": date(2026, 10, 6),
            "transaction_type": kind,
            "direction": "OUT",
            "amount": Decimal("100.50"),
        },
        {
            "transaction_date": date(2026, 10, 6),
            "transaction_type": "TRANSFER",
            "direction": "OUT",
            "amount": Decimal("999"),
        },
        {
            "transaction_date": date(2026, 10, 6),
            "transaction_type": "OTHER",
            "direction": "IN",
            "amount": Decimal("500"),
        },
    ]
    result = with_total_expenses(series, ledger)
    assert [point["total_expenses"] for point in result] == [Decimal("4000.25"), Decimal("4100.75")]
    assert "total_expenses" not in series[0]


def test_total_expense_line_with_no_payments_or_points():
    series = [{"period_start": date(2026, 10, 4)}]
    assert with_total_expenses(series, [])[0]["total_expenses"] == Decimal("0")
    assert with_total_expenses([], []) == []
