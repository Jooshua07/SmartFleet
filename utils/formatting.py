from datetime import date
from decimal import Decimal


def format_kwacha(amount: Decimal | float | int | None) -> str:
    value = Decimal("0.00") if amount is None else Decimal(str(amount))
    return f"K{value:,.2f}"


def format_whole_kwacha(amount: Decimal | float | int | None) -> str:
    value = Decimal("0") if amount is None else Decimal(str(amount))
    return f"K{value:,.0f}"


def format_date(value: date | None) -> str:
    if value is None:
        return "Not set"
    return value.strftime("%d %b %Y")


def bus_status_label(status: str | None) -> str:
    if status == "INACTIVE":
        return "Deactivated"
    if status == "ACTIVE":
        return "Active"
    return status or "Unknown"

