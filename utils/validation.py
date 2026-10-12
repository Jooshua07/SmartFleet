from decimal import Decimal, InvalidOperation


def clean_required_text(value: str | None, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


def clean_optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def parse_optional_positive_int(value: str | int | None, field_name: str) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a whole number.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return parsed


def parse_positive_amount(value: str | int | float | Decimal, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid amount.") from exc
    if not amount.is_finite():
        raise ValueError(f"{field_name} must be a valid amount.")
    if amount <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return amount


def parse_non_negative_amount(value: str | int | float | Decimal, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid amount.") from exc
    if not amount.is_finite():
        raise ValueError(f"{field_name} must be a valid amount.")
    if amount < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return amount
