from datetime import date
from decimal import Decimal

import pytest

from smartfleet_web.reporting import bar_data, choose_period


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
