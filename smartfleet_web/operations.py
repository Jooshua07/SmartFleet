"""Servicing, reminders and consistent-snapshot reporting; no production setup."""

from io import BytesIO

import psycopg
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
)

from database.connection import get_connection, shared_transaction
from services import business_report_service as reports
from services import maintenance_service as maintenance
from services import reminder_service as reminders
from services import report_export_service as exports
from services.bus_service import get_all_buses
from services.preset_service import get_reporting_baseline_date
from smartfleet_web.auth import owner_required
from smartfleet_web.commands import decode_token, execute_command, form_token
from smartfleet_web.management import date_value, field, money_value, positive_id, snapshot
from smartfleet_web.recording import COMMAND_TABLES, checked_date, safe_error
from smartfleet_web.reporting import choose_period
from utils.dates import today_lusaka

bp = Blueprint("operations", __name__)
OPERATION_TABLES = ("maintenance", "maintenance_schedules", "correction_audit", "buses")


def state(connection):
    return snapshot(connection, tuple(dict.fromkeys((*COMMAND_TABLES, *OPERATION_TABLES))))


def perform(action, data, token, operation):
    decoded = decode_token(token, action)
    reason = request.form.get("reason", "").strip()
    if not reason or len(reason) > 500 or any(len(str(v)) > 500 for v in data.values()):
        raise ValueError("Enter a reason and keep each field within 500 characters.")
    settings = current_app.config.get("WRITE_DB_SETTINGS")
    if not settings:
        raise ValueError("The isolated financial environment is not configured.")
    return execute_command(
        settings,
        current_app.config["OWNER_USERNAME"],
        decoded["key"],
        action,
        {k: v for k, v in data.items() if k not in {"csrf_token", "command_token"}},
        "reference-data",
        reason,
        state,
        operation,
        decoded["version"],
    )


@bp.get("/servicing")
@owner_required
def servicing():
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        history = maintenance.get_servicing_history()
        schedules = maintenance.get_servicing_schedules()
    return render_template(
        "servicing.html",
        title="Servicing",
        active="more",
        history=history,
        schedules=schedules,
        today=today_lusaka(),
        warning=maintenance.servicing_warning,
    )


@bp.route("/record-servicing", methods=["GET", "POST"], defaults={"event_id": None})
@bp.route("/servicing/<int:event_id>/edit", methods=["GET", "POST"])
@owner_required
def record_servicing(event_id):
    action = f"servicing:{event_id or 'new'}"
    data = {}
    with get_connection() as connection:
        if event_id:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT * FROM maintenance WHERE id=%s AND is_servicing AND status='COMPLETED'",
                    (event_id,),
                )
                row = cursor.fetchone()
            if row is None:
                abort(404)
            data = dict(
                bus_id=row["bus_id"],
                completed_date=row["completed_date"],
                labour=row["labour_cost"],
                transport=row["transport_cost"],
                other=row["parts_cost"],
                payment_date=row["payment_date"] or "",
                notes=row["notes"] or "",
            )
        token = (
            request.form.get("command_token", "")
            if request.method == "POST"
            else form_token(action, state(connection))
        )
    if request.method == "GET" and not event_id and request.args.get("bus_id"):
        try:
            data["bus_id"] = positive_id(request.args, "bus_id")
        except ValueError:
            abort(400)
    data = dict(request.form) if request.method == "POST" else data
    error, status = None, 200
    if request.method == "POST":
        try:

            def operation():
                bus_id = positive_id(data, "bus_id")
                amounts = {key: money_value(data, key) for key in ("labour", "transport", "other")}
                completed = checked_date(data, "completed_date")
                paid = checked_date(data, "payment_date") if sum(amounts.values()) else None
                return maintenance.record_servicing(
                    bus_id,
                    completed,
                    **amounts,
                    payment_date=paid,
                    notes=data.get("notes", ""),
                    event_id=event_id,
                    reason=data.get("reason"),
                )

            perform(action, data, token, operation)
            flash("Servicing saved.", "success")
            return redirect("/record-servicing" if not event_id else "/servicing", code=303)
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
    buses = get_all_buses()
    if (
        request.method == "GET"
        and data.get("bus_id")
        and not any(b["id"] == data["bus_id"] for b in buses)
    ):
        abort(404)
    fields = [
        field("bus_id", "Bus", "select", [(str(b["id"]), b["registration_number"]) for b in buses]),
        field("completed_date", "Actual completion date", "date", value=today_lusaka()),
        *[
            field(key, label + " (K)", "money", value="0")
            for key, label in (
                ("labour", "Labour"),
                ("transport", "Transport"),
                ("other", "Other costs"),
            )
        ],
        field("payment_date", "Actual payment date", "date", required=False),
        field("notes", "Notes", required=False),
    ]
    for item in fields:
        item["value"] = data.get(item["name"], item["value"])
    return render_template(
        "servicing_form.html",
        title="Correct Servicing" if event_id else "Record Servicing",
        active="more",
        fields=fields,
        command_token=token,
        reason=data.get("reason", ""),
        cancel_url="/servicing",
        error=error,
    ), status


@bp.route("/servicing/schedule/<int:bus_id>", methods=["GET", "POST"])
@owner_required
def schedule(bus_id):
    action = f"servicing-schedule:{bus_id}"
    row = next((r for r in maintenance.get_servicing_schedules() if r["bus_id"] == bus_id), None)
    if row is None:
        abort(404)
    with get_connection() as connection:
        token = (
            request.form.get("command_token", "")
            if request.method == "POST"
            else form_token(action, state(connection))
        )
    data = dict(request.form) if request.method == "POST" else row
    error, status = None, 200
    if request.method == "POST":
        try:

            def operation():
                interval = positive_id(data, "interval_days")
                if interval > 3650:
                    raise ValueError("Choose a frequency of 1 to 3650 days.")
                maintenance.set_servicing_schedule(
                    bus_id, date_value(data, "next_due_date"), interval, data.get("reason")
                )
                return {"bus_id": bus_id}

            perform(action, data, token, operation)
            flash("Servicing schedule saved.", "success")
            return redirect("/servicing", code=303)
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
    fields = [
        field("next_due_date", "Next servicing due", "date", value=data.get("next_due_date") or ""),
        field("interval_days", "Frequency (days)", "number", value=data.get("interval_days") or 35),
    ]
    return render_template(
        "manage_form.html",
        title="Servicing Schedule - " + row["registration_number"],
        active="more",
        fields=fields,
        command_token=token,
        reason=data.get("reason", ""),
        cancel_url="/servicing",
        error=error,
    ), status


@bp.get("/reminders")
@owner_required
def reminder_list():
    today = today_lusaka()
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        groups = [
            ("Servicing due", reminders.get_due_maintenance(today)),
            ("Deactivated buses", reminders.get_deactivated_buses()),
            ("Document expiry", reminders.get_document_expiries(today)),
            ("Pending reminders", reminders.get_open_reminders()),
        ]
    return render_template(
        "reminders.html",
        title="Reminders",
        active="more",
        groups=groups,
        today=today,
        warning=maintenance.servicing_warning,
    )


def report_data(args):
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        connection.execute("SET LOCAL statement_timeout='15s'")
        baseline = get_reporting_baseline_date()
        start, end = choose_period(args, baseline, today_lusaka())
        # Bound the expensive historical cross-join and in-memory workbook before loading rows.
        count = connection.execute(
            "SELECT (SELECT count(*) FROM financial_transactions WHERE transaction_date BETWEEN %s AND %s), (SELECT count(*) FROM buses)",
            (baseline, end),
        ).fetchone()
        if count[0] > 10000 or count[1] * ((end - start).days + 1) > 200000:
            raise ValueError(
                "This report exceeds the local resource limit. Choose a shorter period."
            )
        report = reports.get_business_report(start, end)
        reconciliation = reports.get_reconciliation(end)
        tables = exports.report_export_tables(report)
        tables.update(
            {
                "Servicing History": report["history"],
                "Servicing Schedules": report["schedules"],
                "Reconciliation": reconciliation["movements"],
                "Ledger": reconciliation["ledger"],
            }
        )
        tables["Business Summary"] = [
            {
                "Start": start,
                "End": end,
                **report["operating"],
                **{
                    f"Cash {k}": v
                    for k, v in report["balance"].items()
                    if not isinstance(v, (dict, list))
                },
            }
        ]
        if sum(len(rows) for rows in tables.values()) > 50000:
            raise ValueError("Too many report rows. Choose a shorter period.")
    return report, reconciliation, tables


@bp.get("/reports")
@owner_required
def report():
    try:
        data, reconciliation, tables = report_data(request.args)
    except ValueError as exc:
        return render_template("error.html", code=400, message=str(exc)), 400
    return render_template(
        "reports.html",
        title="Reports",
        active="more",
        report=data,
        reconciliation=reconciliation,
        tables=tables,
        start=data["start"],
        end=data["end"],
        period_mode=request.args.get("period", "1m"),
        custom_mode=request.args.get("custom", "all"),
    )


@bp.get("/reports/export")
@owner_required
def export():
    kind, table = request.args.get("format", "xlsx"), request.args.get("table", "all")
    if kind not in {"csv", "xlsx"} or (kind == "csv" and table == "all"):
        abort(400)
    try:
        data, _, tables = report_data(request.args)
        if table != "all" and table not in tables:
            abort(400)
        selected = tables if table == "all" else {table: tables[table]}
        content = (
            exports.csv_export(selected[table]) if kind == "csv" else exports.excel_export(selected)
        )
        if len(content) > 20 * 1024 * 1024:
            raise ValueError("Export too large. Choose a shorter period.")
    except ValueError as exc:
        return render_template("error.html", code=400, message=str(exc)), 400
    mimetype = (
        "text/csv"
        if kind == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return send_file(
        BytesIO(content),
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"smartfleet-{data['start']}-{data['end']}.{kind}",
    )
