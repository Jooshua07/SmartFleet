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

