"""Pure calculation checks for complete cashing invoices."""

from decimal import Decimal

import pytest

from smartfleet_web.cashing_entry import complete_allocations


def preview(count=3):
    return {
        "buses": [
            dict(
                id=i,
                normal_days=3,
                normal_daily_rate=Decimal("600.25"),
                sunday_rate=Decimal("300"),
                expected_amount=Decimal("1800.75"),
            )
            for i in range(1, count + 1)
        ],
        "expected_total": Decimal("1800.75") * count,
        "previous_sunday": None,
    }


@pytest.mark.parametrize("count", [1, 2, 3, 7])
def test_standard_complete_decimal_invoice_ignores_forged_subset_amount(count):
    result = complete_allocations(
        {
            "mode": "STANDARD",
            "bus_ids": ["1"],
            "total_received": "1",
            "adjust_ids": ["1"],
            "amount_1": "0",
        },
        preview(count),
    )
    assert len(result["entries"]) == count
    assert result["total_received"] == Decimal("1800.75") * count
    assert all(e["actual_amount"] == Decimal("1800.75") for e in result["entries"])
    assert result["unallocated_amount"] == 0


@pytest.mark.parametrize("value", ["", "NaN", "-1", "1.001", "Infinity"])
def test_selected_blank_or_invalid_never_becomes_zero(value):
    with pytest.raises(ValueError):
        complete_allocations(
            {"mode": "ADJUSTED", "adjust_ids": ["1"], "amount_1": value}, preview()
        )


def test_explicit_zero_retains_other_bus_expectations():
    result = complete_allocations(
        {
            "mode": "ADJUSTED",
            "adjust_ids": ["1"],
            "amount_1": "0",
            "classification_1": "UNKNOWN_DIFFERENCE",
            "explanation_1": "No cash received",
        },
        preview(),
    )
    assert result["total_received"] == Decimal("3601.50")
    assert [e["actual_amount"] for e in result["entries"]] == [
        0,
        Decimal("1800.75"),
        Decimal("1800.75"),
    ]


def test_no_eligible_and_duplicate_adjustment_rejected():
    with pytest.raises(ValueError, match="No buses"):
        complete_allocations({"mode": "STANDARD"}, preview(0))
    with pytest.raises(ValueError, match="different eligible"):
        complete_allocations({"mode": "ADJUSTED", "adjust_ids": ["1", "1"]}, preview())
