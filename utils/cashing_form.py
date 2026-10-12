from __future__ import annotations

from collections.abc import MutableMapping
from decimal import Decimal, InvalidOperation


CASHING_FORM_VERSION_KEY = "cashing_form_version"
CASHING_FORM_KEY_PREFIX = "cash_direct_"


def bus_option_label(bus: dict) -> str:
    driver_name = bus.get("driver_name") or "No assigned driver"
    return f"{bus['registration_number']} | {driver_name}"


def _amount(value, field_name: str) -> Decimal:
    if value is None or value == "":
        raise ValueError(f"{field_name} is required.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid amount.") from exc
    if amount < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return amount.quantize(Decimal("0.01"))


def build_direct_cashing_entries(
    selected_bus_ids: list[int],
    normal_amounts: dict[int, object],
    sunday_amounts: dict[int, object] | None = None,
    reasons: dict[int, str | None] | None = None,
    notes: dict[int, str | None] | None = None,
) -> list[dict]:
    if not selected_bus_ids:
        raise ValueError("Choose at least one bus.")

    sunday_amounts = sunday_amounts or {}
    reasons = reasons or {}
    notes = notes or {}
    entries = []

    for bus_id in selected_bus_ids:
        normal_amount = _amount(normal_amounts.get(bus_id), "Amount")
        sunday_amount = _amount(sunday_amounts.get(bus_id, 0), "Sunday amount")
        actual_amount = normal_amount + sunday_amount
        if actual_amount <= 0:
            raise ValueError("Enter an amount for each selected bus.")

        entries.append(
            {
                "include": True,
                "bus_id": bus_id,
                "normal_amount": normal_amount,
                "sunday_amount": sunday_amount,
                "actual_amount": actual_amount,
                "explanation": (reasons.get(bus_id) or "").strip() or None,
                "notes": (notes.get(bus_id) or "").strip() or None,
            }
        )

    return entries


def clear_cashing_form_state(state: MutableMapping) -> None:
    current_version = int(state.get(CASHING_FORM_VERSION_KEY, 0))
    state[CASHING_FORM_VERSION_KEY] = current_version + 1
