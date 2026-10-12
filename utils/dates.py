from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


BUSINESS_TIMEZONE = ZoneInfo("Africa/Lusaka")


def today_lusaka() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()


def week_bounds(day: date | None = None) -> tuple[date, date]:
    current = day or today_lusaka()
    start = current - timedelta(days=current.weekday())
    return start, start + timedelta(days=6)


def month_bounds(day: date | None = None) -> tuple[date, date]:
    current = day or today_lusaka()
    start = current.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month - timedelta(days=1)


def period_bounds(mode: str, day: date | None = None) -> tuple[date, date]:
    if mode == "Month":
        return month_bounds(day)
    return week_bounds(day)


def subtract_months(day: date, months: int) -> date:
    month_index = day.month - months
    year = day.year
    while month_index <= 0:
        month_index += 12
        year -= 1

    month_lengths = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    target_day = min(day.day, month_lengths[month_index - 1])
    return day.replace(year=year, month=month_index, day=target_day)


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

