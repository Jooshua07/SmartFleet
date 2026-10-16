"""Effective-dated collection coverage; legacy Thursday/Sunday rules are the initial presets."""

from datetime import date, timedelta

from psycopg.rows import dict_row

from database.connection import get_connection
from services.preset_service import list_cashing_schedule_rules

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def applicable_rules(rules, on_date):
    return [
        r
        for r in rules
        if r["effective_from"] <= on_date
        and (r.get("effective_to") is None or r["effective_to"] >= on_date)
    ]


def coverage_from_rules(collection_date, rules):
    if not isinstance(collection_date, date):
        raise ValueError("Collection date is required.")
    matching = [
        r
        for r in applicable_rules(rules, collection_date)
        if r["collection_day"] == collection_date.isoweekday()
    ]
    if len(matching) != 1:
        raise ValueError("Choose a collection date in the applicable schedule.")
    rule = matching[0]
    dates = sorted(
        collection_date - timedelta(days=(collection_date.isoweekday() - d) % 7 or 7)
        for d in rule["covered_days"]
    )
    if (
        not dates
        or any(d.isoweekday() == 7 for d in dates)
        or any((b - a).days != 1 for a, b in zip(dates, dates[1:]))
    ):
        raise ValueError("Normal coverage must be consecutive Monday-Saturday days.")
    sunday = None
    if rule["include_previous_sunday"]:
        sunday = collection_date - timedelta(days=collection_date.isoweekday() % 7 or 7)
    return {
        "collection_type": DAY_NAMES[collection_date.weekday()].upper(),
        "coverage_start": dates[0],
        "coverage_end": dates[-1],
        "previous_sunday": sunday,
    }


def get_scheduled_coverage(collection_date):
    return coverage_from_rules(collection_date, list_cashing_schedule_rules())


def validate_week(pattern):
    if not pattern or len(pattern) > 7:
        raise ValueError("Choose collection days and coverage.")
    collection_days = [r["collection_day"] for r in pattern]
    covered = [d for r in pattern for d in r["covered_days"]]
    if (
        any(d not in range(1, 8) for d in collection_days)
        or len(set(collection_days)) != len(collection_days)
        or sorted(covered) != [1, 2, 3, 4, 5, 6]
        or sum(bool(r["include_previous_sunday"]) for r in pattern) != 1
    ):
        raise ValueError("Cover Monday-Saturday exactly once, with one optional Sunday collection.")
    for rule in pattern:
        sample = date(2026, 10, 19) + timedelta(days=rule["collection_day"] - 1)
        coverage_from_rules(sample, [{**rule, "effective_from": date.min, "effective_to": None}])


def replace_schedule(pattern, effective_from, reason):
    validate_week(pattern)
    if not isinstance(effective_from, date):
        raise ValueError("Effective date is required.")
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM cashing_schedule_rules ORDER BY effective_from FOR UPDATE"
            )
            existing = cursor.fetchall()
            if existing and effective_from <= max(r["effective_from"] for r in existing):
                raise ValueError("Choose a date after the latest schedule starts.")
            cursor.execute(
                "SELECT 1 FROM remittance_collections WHERE collection_date >= %s LIMIT 1",
                (effective_from - timedelta(days=7),),
            )
            if cursor.fetchone():
                raise ValueError(
                    "Recorded collections may be affected. Choose a later effective date."
                )
            proposed = [
                {**r, "effective_to": effective_from - timedelta(days=1)}
                if r.get("effective_to") is None
                else r
                for r in existing
            ]
            proposed += [
                {**r, "effective_from": effective_from, "effective_to": None} for r in pattern
            ]
            # Check the transition as dates, not just weekdays, to prevent missed/double-covered work.
            counts = {}
            for offset in range(-14, 22):
                collection_date = effective_from + timedelta(days=offset)
                for rule in applicable_rules(proposed, collection_date):
                    if rule["collection_day"] != collection_date.isoweekday():
                        continue
                    coverage = coverage_from_rules(collection_date, [rule])
                    day = coverage["coverage_start"]
                    while day <= coverage["coverage_end"]:
                        counts[day] = counts.get(day, 0) + 1
                        day += timedelta(days=1)
                    sunday = coverage["previous_sunday"]
                    if sunday:
                        counts[sunday] = counts.get(sunday, 0) + 1
            if existing and any(
                counts.get(effective_from + timedelta(days=i), 0) != 1 for i in range(-7, 8)
            ):
                raise ValueError(
                    "This transition skips or repeats work days. Choose another effective date."
                )
            cursor.execute(
                "UPDATE cashing_schedule_rules SET active=FALSE,effective_to=%s "
                "WHERE effective_to IS NULL",
                (effective_from - timedelta(days=1),),
            )
            for rule in pattern:
                cursor.execute(
                    """INSERT INTO cashing_schedule_rules
                    (collection_day,covered_days,include_previous_sunday,effective_from,notes)
                    VALUES (%s,%s,%s,%s,%s)""",
                    (
                        rule["collection_day"],
                        sorted(rule["covered_days"]),
                        rule["include_previous_sunday"],
                        effective_from,
                        reason,
                    ),
                )
    return {"effective_from": effective_from, "collection_days": collection_days(pattern)}


def collection_days(pattern):
    return sorted(r["collection_day"] for r in pattern)
