from datetime import date, timedelta
from decimal import Decimal

from psycopg.rows import dict_row

from database.connection import get_connection
from utils.validation import clean_optional_text, parse_non_negative_amount, parse_positive_amount


DEFAULT_COLLECTION_ACCOUNT_TYPE = "AIRTEL_MONEY"
REPORTING_BASELINE_SETTING = "REPORTING_BASELINE_DATE"


def _coerce_date(value: date, field_name: str) -> date:
    if not isinstance(value, date):
        raise ValueError(f"{field_name} is required.")
    return value


def _record_audit(
    cursor,
    preset_area: str,
    preset_key: str,
    old_value,
    new_value,
    effective_date: date | None = None,
    notes: str | None = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO business_preset_audit (
            preset_area,
            preset_key,
            old_value,
            new_value,
            effective_date,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (
            preset_area,
            preset_key,
            None if old_value is None else str(old_value),
            str(new_value),
            effective_date,
            clean_optional_text(notes),
        ),
    )


def get_business_settings() -> dict[str, dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT setting_key, setting_value, setting_type, notes
                FROM business_settings
                ORDER BY setting_key;
                """
            )
            return {row["setting_key"]: row for row in cursor.fetchall()}


def get_business_setting(setting_key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT setting_value
                FROM business_settings
                WHERE setting_key = %s;
                """,
                (setting_key,),
            )
            row = cursor.fetchone()
            return row["setting_value"] if row else default


def get_reporting_baseline_date() -> date:
    value = get_business_setting(REPORTING_BASELINE_SETTING, "2026-10-01")
    return date.fromisoformat(value)


def set_reporting_baseline_date(baseline_date: date, notes: str | None = None) -> None:
    baseline_date = _coerce_date(baseline_date, "Reporting baseline date")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT setting_value
                FROM business_settings
                WHERE setting_key = %s
                FOR UPDATE;
                """,
                (REPORTING_BASELINE_SETTING,),
            )
            existing = cursor.fetchone()
            old_value = existing["setting_value"] if existing else None
            cursor.execute(
                """
                INSERT INTO business_settings (setting_key, setting_value, setting_type, notes)
                VALUES (%s, %s, 'DATE', %s)
                ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (REPORTING_BASELINE_SETTING, baseline_date.isoformat(), clean_optional_text(notes)),
            )
            _record_audit(
                cursor,
                "REPORTING",
                REPORTING_BASELINE_SETTING,
                old_value,
                baseline_date.isoformat(),
                baseline_date,
                notes,
            )


def get_default_collection_account_type() -> str:
    return get_business_setting(
        "DEFAULT_COLLECTION_ACCOUNT_TYPE",
        DEFAULT_COLLECTION_ACCOUNT_TYPE,
    ) or DEFAULT_COLLECTION_ACCOUNT_TYPE


def list_cashing_rates() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, rate_type, amount, active, effective_from, effective_to, notes
                FROM cashing_rates
                ORDER BY rate_type, effective_from DESC, id DESC;
                """
            )
            return cursor.fetchall()


def get_effective_cashing_rates(on_date: date) -> dict[str, Decimal]:
    on_date = _coerce_date(on_date, "Rate date")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ON (rate_type)
                    rate_type,
                    amount
                FROM cashing_rates
                WHERE effective_from <= %s
                  AND (effective_to IS NULL OR effective_to >= %s)
                ORDER BY rate_type, effective_from DESC, id DESC;
                """,
                (on_date, on_date),
            )
            return {row["rate_type"]: row["amount"] for row in cursor.fetchall()}


def set_cashing_rate(
    rate_type: str,
    amount,
    effective_from: date,
    notes: str | None = None,
) -> dict:
    if rate_type not in {"NORMAL_DAY", "SUNDAY"}:
        raise ValueError("Cashing rate type is not supported.")
    amount = parse_non_negative_amount(amount, "Cashing rate")
    effective_from = _coerce_date(effective_from, "Effective date")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, amount, effective_from
                FROM cashing_rates
                WHERE rate_type = %s
                  AND active = TRUE
                FOR UPDATE;
                """,
                (rate_type,),
            )
            current = cursor.fetchone()
            if current and effective_from <= current["effective_from"]:
                raise ValueError("Use an effective date after the current active rate start date.")

            if current:
                cursor.execute(
                    """
                    UPDATE cashing_rates
                    SET active = FALSE,
                        effective_to = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                    """,
                    (effective_from - timedelta(days=1), current["id"]),
                )

            cursor.execute(
                """
                INSERT INTO cashing_rates (rate_type, amount, active, effective_from, notes)
                VALUES (%s, %s, TRUE, %s, %s)
                RETURNING id, rate_type, amount, active, effective_from, effective_to, notes;
                """,
                (rate_type, amount, effective_from, clean_optional_text(notes)),
            )
            new_rate = cursor.fetchone()
            _record_audit(
                cursor,
                "CASHING_RATE",
                rate_type,
                None if current is None else current["amount"],
                amount,
                effective_from,
                notes,
            )
            return new_rate


def list_cashing_schedule_rules() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, collection_day, covered_days, include_previous_sunday,
                       active, effective_from, effective_to, notes
                FROM cashing_schedule_rules
                ORDER BY collection_day, effective_from DESC;
                """
            )
            return cursor.fetchall()


def set_cashing_schedule_rule(
    collection_day: int,
    covered_days: list[int],
    include_previous_sunday: bool,
    effective_from: date,
    notes: str | None = None,
) -> dict:
    if collection_day not in range(1, 8):
        raise ValueError("Collection day is not supported.")
    if not covered_days:
        raise ValueError("Choose at least one covered day.")
    cleaned_days = sorted(set(int(day) for day in covered_days))
    if any(day not in range(1, 8) for day in cleaned_days):
        raise ValueError("Covered days must be Monday through Sunday.")
    effective_from = _coerce_date(effective_from, "Effective date")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, covered_days, effective_from
                FROM cashing_schedule_rules
                WHERE collection_day = %s
                  AND active = TRUE
                ORDER BY effective_from DESC, id DESC
                LIMIT 1
                FOR UPDATE;
                """,
                (collection_day,),
            )
            current = cursor.fetchone()
            if current and effective_from <= current["effective_from"]:
                raise ValueError("Use an effective date after the current active schedule start date.")

            if current:
                cursor.execute(
                    """
                    UPDATE cashing_schedule_rules
                    SET active = FALSE,
                        effective_to = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                    """,
                    (effective_from - timedelta(days=1), current["id"]),
                )

            cursor.execute(
                """
                INSERT INTO cashing_schedule_rules (
                    collection_day,
                    covered_days,
                    include_previous_sunday,
                    active,
                    effective_from,
                    notes
                )
                VALUES (%s, %s, %s, TRUE, %s, %s)
                RETURNING id, collection_day, covered_days, include_previous_sunday,
                          active, effective_from, effective_to, notes;
                """,
                (
                    collection_day,
                    cleaned_days,
                    include_previous_sunday,
                    effective_from,
                    clean_optional_text(notes),
                ),
            )
            rule = cursor.fetchone()
            _record_audit(
                cursor,
                "CASHING_SCHEDULE",
                str(collection_day),
                None if current is None else current["covered_days"],
                cleaned_days,
                effective_from,
                notes,
            )
            return rule


def list_driver_salary_presets() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    dsp.id,
                    dsp.driver_id,
                    d.full_name AS driver_name,
                    dsp.monthly_salary,
                    dsp.active,
                    dsp.effective_from,
                    dsp.effective_to,
                    dsp.notes
                FROM driver_salary_presets dsp
                LEFT JOIN drivers d ON d.id = dsp.driver_id
                ORDER BY dsp.driver_id NULLS FIRST, dsp.effective_from DESC, dsp.id DESC;
                """
            )
            return cursor.fetchall()


def set_driver_salary_preset(
    monthly_salary,
    effective_from: date,
    driver_id: int | None = None,
    notes: str | None = None,
) -> dict:
    monthly_salary = parse_positive_amount(monthly_salary, "Monthly salary")
    effective_from = _coerce_date(effective_from, "Effective date")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            if driver_id is not None:
                cursor.execute("SELECT id FROM drivers WHERE id = %s;", (driver_id,))
                if cursor.fetchone() is None:
                    raise ValueError("Choose a valid driver.")

            driver_clause = "driver_id IS NULL" if driver_id is None else "driver_id = %s"
            params = [] if driver_id is None else [driver_id]
            cursor.execute(
                f"""
                SELECT id, monthly_salary, effective_from
                FROM driver_salary_presets
                WHERE {driver_clause}
                  AND active = TRUE
                FOR UPDATE;
                """,
                params,
            )
            current = cursor.fetchone()
            if current and effective_from <= current["effective_from"]:
                raise ValueError("Use an effective date after the current active salary start date.")

            if current:
                cursor.execute(
                    """
                    UPDATE driver_salary_presets
                    SET active = FALSE,
                        effective_to = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                    """,
                    (effective_from - timedelta(days=1), current["id"]),
                )

            cursor.execute(
                """
                INSERT INTO driver_salary_presets (
                    driver_id,
                    monthly_salary,
                    active,
                    effective_from,
                    notes
                )
                VALUES (%s, %s, TRUE, %s, %s)
                RETURNING id, driver_id, monthly_salary, active, effective_from, effective_to, notes;
                """,
                (driver_id, monthly_salary, effective_from, clean_optional_text(notes)),
            )
            preset = cursor.fetchone()
            _record_audit(
                cursor,
                "DRIVER_SALARY",
                "DEFAULT" if driver_id is None else str(driver_id),
                None if current is None else current["monthly_salary"],
                monthly_salary,
                effective_from,
                notes,
            )
            return preset


def list_reminder_presets() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT preset_key, warning_days, active, notes
                FROM reminder_presets
                ORDER BY preset_key;
                """
            )
            return cursor.fetchall()


def set_reminder_preset(
    preset_key: str,
    warning_days: int,
    active: bool = True,
    notes: str | None = None,
) -> dict:
    if preset_key not in {
        "MAINTENANCE_WARNING_DAYS",
        "DOCUMENT_EXPIRY_WARNING_DAYS",
        "OVERDUE_CASHING_WARNING_DAYS",
    }:
        raise ValueError("Reminder preset is not supported.")
    if int(warning_days) < 0:
        raise ValueError("Warning days cannot be negative.")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT warning_days
                FROM reminder_presets
                WHERE preset_key = %s
                FOR UPDATE;
                """,
                (preset_key,),
            )
            current = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO reminder_presets (preset_key, warning_days, active, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (preset_key) DO UPDATE
                SET warning_days = EXCLUDED.warning_days,
                    active = EXCLUDED.active,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING preset_key, warning_days, active, notes;
                """,
                (preset_key, int(warning_days), active, clean_optional_text(notes)),
            )
            preset = cursor.fetchone()
            _record_audit(
                cursor,
                "REMINDER",
                preset_key,
                None if current is None else current["warning_days"],
                warning_days,
                None,
                notes,
            )
            return preset

