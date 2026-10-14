from datetime import date, timedelta

from utils.dates import subtract_months, today_lusaka


def reporting_period(mode: str, baseline: date, today: date | None = None,
                     start: date | None = None, end: date | None = None) -> tuple[date, date]:
    today = today or today_lusaka()
    if mode == 'Custom':
        if not isinstance(start, date) or not isinstance(end, date):
            raise ValueError('Choose a start and end date.')
        if end < start:
            raise ValueError('End date must be on or after start date.')
        return start, end
    months = {'Month': 1, '3 Months': 3, '6 Months': 6}.get(mode)
    if months is None:
        raise ValueError('Choose a supported reporting period.')
    return max(baseline, subtract_months(today.replace(day=1), months - 1)), today


def scheduled_chart_dates(start: date, end: date) -> list[date]:
    points = []
    day = start
    while day <= end:
        if day.weekday() in (3, 6):
            points.append(day)
        day += timedelta(days=1)
    return points
