"""Read-only, consistent-snapshot views using existing financial services."""

from bisect import bisect_left
from datetime import date
from decimal import Decimal

from flask import current_app, render_template, request
from psycopg.rows import dict_row

from database.connection import shared_transaction
from services import (
    bus_account_service,
    dashboard_service,
    finance_service,
    maintenance_service,
    performance_service,
    preset_service,
    reminder_service,
)
from utils.dates import today_lusaka
from utils.reporting_periods import reporting_period


def choose_period(args, baseline, today, earliest=None):
    mode = args.get("period", "1m")
    if mode in {"1m", "3m"}:
        start, end = reporting_period("Month" if mode == "1m" else "3 Months", baseline, today)
    elif mode == "custom":
        custom = args.get("custom", "all")
        if custom == "all":
            start, end = (
                max(baseline, earliest if earliest and earliest <= today else baseline),
                today,
            )
        elif custom == "6m":
            start, end = reporting_period("6 Months", baseline, today)
        elif custom == "dates":
            start, end = reporting_period(
                "Custom",
                baseline,
                today,
                date.fromisoformat(args.get("start", "")),
                date.fromisoformat(args.get("end", "")),
            )
        else:
            raise ValueError("Choose a supported custom period.")
    else:
        raise ValueError("Choose a supported period.")
    if end < start or (end - start).days > 3660 or end == date.max:
        raise ValueError("Choose an ordered date range of at most ten years.")
    return start, end


def load_report(args, screen="home", bus_id=None):
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        baseline = preset_service.get_reporting_baseline_date()
        today = today_lusaka()
        bounds = dashboard_service.get_activity_date_bounds()
        start, end = choose_period(args, baseline, today, bounds["earliest_date"])
        current = finance_service.get_period_balance(baseline, today)
        selected = finance_service.get_period_balance(start, end)
        result = dict(
            start=start,
            end=end,
            today=today,
            baseline=baseline,
            current=current,
            selected=selected,
            period_mode=args.get("period", "1m"),
            custom_mode=args.get("custom", "all"),
        )
        if screen in {"home", "bus-accounts"}:
            result["fleet"] = bus_account_service.get_bus_contribution_summary(start, end)
        if screen == "home":
            result["counts"] = dashboard_service.get_bus_status_counts()
            result["reminders"] = reminder_service.get_open_reminders(limit=3)
            result["servicing_alerts"] = [
                dict(row, level=maintenance_service.servicing_warning(row["next_due_date"], today))
                for row in maintenance_service.get_servicing_schedules()
                if maintenance_service.servicing_warning(row["next_due_date"], today)
                in {"Warning", "Urgent", "Overdue"}
            ]
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT transaction_date,description,amount,direction FROM financial_transactions WHERE transaction_date BETWEEN %s AND %s ORDER BY transaction_date DESC,id DESC LIMIT 5",
                    (baseline, today),
                )
                result["activity"] = cursor.fetchall()
                cursor.execute("SELECT count(*) AS count FROM drivers")
                result["setup_warnings"] = (
                    ["No drivers have been added yet."] if cursor.fetchone()["count"] == 0 else []
                )
            series = performance_service.get_business_financial_timeline(start, end)
            if series and series[-1]["period_start"] != end:
                series.append(
                    {**series[-1], "period_start": end, "period_end": end, "period_end_point": True}
                )
            series = with_total_expenses(
                series, finance_service.get_period_ledger(max(start, baseline), end)
            )
            result["series"] = series
            result["chart_data"] = {
                "timeline": {
                    "labels": [str(r["period_start"]) for r in series],
                    "datasets": [
                        {
                            "label": label,
                            "data": [float(r[key]) for r in series],
                            "borderColor": color,
                            "backgroundColor": color,
                        }
                        for key, label, color in [
                            ("revenue", "Revenue", "#187454"),
                            ("total_expenses", "Total Expenses", "#c34b50"),
                            ("business_balance", "Business balance", "#1479f6"),
                        ]
                    ],
                },
                "bars": bar_data(result["fleet"]["buses"], "registration_number"),
            }
        if screen == "finance":
            result["operating"] = dashboard_service.get_financial_summary(start, end)
            try:
                page = int(args.get("page", "1"))
                if not 1 <= page <= 10000:
                    raise ValueError
            except ValueError:
                raise ValueError("Choose a valid page.") from None
            section = args.get("view", "general")
            if section not in {"general", "collections", "expenses", "balances"}:
                raise ValueError("Choose a finance section.")
            queries = {
                "general": "SELECT transaction_date AS day,description AS title,amount,direction,id FROM financial_transactions WHERE transaction_date BETWEEN %s AND %s AND transaction_type<>'TRANSFER' ORDER BY transaction_date DESC,id DESC LIMIT 21 OFFSET %s",
                "balances": "SELECT transaction_date AS day,description AS title,amount,direction,id FROM financial_transactions WHERE transaction_date BETWEEN %s AND %s ORDER BY transaction_date DESC,id DESC LIMIT 21 OFFSET %s",
                "collections": "SELECT collection_date AS day,'Cashing collection' AS title,total_amount AS amount,'IN' AS direction,id FROM remittance_collections WHERE collection_date BETWEEN %s AND %s ORDER BY collection_date DESC,id DESC LIMIT 21 OFFSET %s",
                "expenses": "SELECT expense_date AS day,description AS title,amount,'OUT' AS direction,id FROM expenses WHERE expense_date BETWEEN %s AND %s ORDER BY expense_date DESC,id DESC LIMIT 21 OFFSET %s",
            }
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(queries[section], (max(start, baseline), end, (page - 1) * 20))
                rows = cursor.fetchall()
            result.update(section=section, rows=rows[:20], page=page, has_next=len(rows) > 20)
        if bus_id is not None:
            detail = bus_account_service.get_bus_account_detail(bus_id, start, end)
            summary = next((r for r in result["fleet"]["buses"] if r["bus_id"] == bus_id), None)
            if summary is None:
                raise ValueError("Bus not found.")
            result.update(detail=detail, bus_summary=summary)
            result["chart_data"] = {"bars": bar_data(detail["trend"], "month")}
        elif screen == "bus-accounts":
            result["chart_data"] = {
                "bars": bar_data(result["fleet"]["buses"], "registration_number")
            }
    return result


def with_total_expenses(series, ledger):
    dates = [point["period_start"] for point in series]
    buckets = [Decimal("0") for _ in series]
    for row in ledger:
        if row["direction"] == "OUT" and row["transaction_type"] != "TRANSFER":
            index = bisect_left(dates, row["transaction_date"])
            if index < len(buckets):
                buckets[index] += row["amount"]
    total = Decimal("0")
    result = []
    for point, amount in zip(series, buckets, strict=True):
        total += amount
        result.append({**point, "total_expenses": total})
    return result


def bar_data(rows, label):
    return {
        "labels": [str(r[label]) for r in rows],
        "datasets": [
            {
                "label": "Revenue",
                "data": [float(r["recorded_revenue"]) for r in rows],
                "backgroundColor": "#187454",
            },
            {
                "label": "Attributed costs",
                "data": [float(r["attributed_costs"]) for r in rows],
                "backgroundColor": "#c34b50",
            },
        ],
    }


def show(screen="home", bus_id=None):
    try:
        data = load_report(request.args, screen, bus_id)
    except ValueError as exc:
        return render_template("error.html", code=400, message=str(exc)), 400
    return render_template(
        {
            "home": "dashboard.html",
            "finance": "finance_report.html",
            "bus-accounts": "bus_accounts.html",
        }[screen],
        title="Home" if screen == "home" else "Finance" if screen == "finance" else "Bus Accounts",
        active="home" if screen == "home" else "finance" if screen == "finance" else "buses",
        **data,
    )
