from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from psycopg.types.json import Jsonb

from utils.validation import clean_required_text


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def record_correction_audit(
    cursor,
    *,
    area: str,
    record_type: str,
    record_id: int,
    action: str,
    reason: str,
    snapshot: dict,
) -> dict:
    reason = clean_required_text(reason, "Correction reason")
    cursor.execute(
        """
        INSERT INTO correction_audit (
            area,
            record_type,
            record_id,
            action,
            reason,
            snapshot
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, corrected_at, area, record_type, record_id, action, reason;
        """,
        (area, record_type, record_id, action, reason, Jsonb(_json_safe(snapshot))),
    )
    return cursor.fetchone()
