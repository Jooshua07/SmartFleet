from decimal import Decimal, InvalidOperation


def clean_required_text(value: str | None, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


def parse_positive_amount(value: str | int | float | Decimal, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid amount.") from exc
    if amount <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return amount

