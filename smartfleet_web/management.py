"""Owner-only reference data and preset workflows; services retain their business rules."""

from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from psycopg import sql
from psycopg.rows import dict_row

from database.connection import get_connection
from services import account_service, bus_service, driver_service, preset_service, route_service
from services.collection_schedule_service import DAY_NAMES, get_scheduled_coverage, replace_schedule
from smartfleet_web.auth import owner_required
from smartfleet_web.commands import CommandConflict, decode_token, execute_command, form_token
from utils.dates import today_lusaka

bp = Blueprint("management", __name__)
TABLES = {
    "bus-new": (
        "buses",
        "bus_status_history",
        "bus_route_history",
        "bus_documents",
        "driver_assignments",
    ),
    "bus-edit": ("buses", "bus_status_history", "bus_route_history"),
    "bus-status": ("buses", "bus_status_history"),
    "route-new": ("routes",),
    "driver-new": ("drivers", "driver_employments"),
    "driver-edit": ("drivers",),
    "account": ("financial_accounts",),
    "rate": ("cashing_rates", "business_preset_audit"),
    "salary": ("driver_salary_presets", "business_preset_audit"),
    "advance": ("business_settings", "business_preset_audit"),
    "reminder": ("reminder_presets", "business_preset_audit"),
    "reporting": ("business_settings", "business_preset_audit"),
    "schedule": ("cashing_schedule_rules",),
}


def snapshot(connection, tables):
    result = {}
    with connection.cursor(row_factory=dict_row) as cursor:
        for table in tables:
            key = (
                "setting_key"
                if table == "business_settings"
                else ("preset_key" if table == "reminder_presets" else "id")
            )
            cursor.execute(
                sql.SQL("SELECT * FROM {} ORDER BY {} LIMIT 5001").format(
                    sql.Identifier(table), sql.Identifier(key)
                )
            )
            result[table] = cursor.fetchall()
            if len(result[table]) > 5000:
                raise ValueError("This register needs a narrower view before editing.")
    return result


def field(name, label, kind="text", options=None, required=True, value=""):
    return {
        "name": name,
        "label": label,
        "type": kind,
        "options": options,
        "required": required,
        "value": value,
    }


def date_value(data, name, optional=False):
    value = data.get(name, "")
    if not value and optional:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("Enter a valid date.") from None


def money_value(data, name):
    try:
        amount = Decimal(data.get(name, ""))
    except InvalidOperation:
        raise ValueError("Enter a valid amount.") from None
    if (
        not amount.is_finite()
        or amount < 0
        or amount >= Decimal("1000000000")
        or amount.as_tuple().exponent < -2
    ):
        raise ValueError("Use a non-negative amount with at most two decimal places.")
    return amount


def positive_id(data, name, optional=False):
    if optional and not data.get(name):
        return None
    try:
        value = int(data[name])
        if value <= 0:
            raise ValueError
        return value
    except (KeyError, ValueError, TypeError):
        raise ValueError("Choose a valid record.") from None


def definition(kind, record_id):
    today = today_lusaka().isoformat()
    existing = {}
    if kind.startswith("bus-") and kind != "bus-new":
        existing = bus_service.get_bus_details(record_id)["bus"]
    elif kind == "driver-edit":
        existing = driver_service.get_driver(record_id)
    elif kind == "account":
        existing = next(
            (r for r in account_service.get_accounts_for_management() if r["id"] == record_id), None
        )
        if existing is None:
            abort(404)
    if kind in {"bus-new", "bus-edit"}:
        routes = [(str(r["id"]), r["name"]) for r in route_service.get_active_routes()]
        fields = [
            field("registration_number", "Registration number"),
            field("route_id", "Route", "select", routes),
            field("date_acquired", "Date acquired", "date", required=False, value=today),
            field("model", "Model", required=False),
            field("seating_capacity", "Seating capacity", "number", required=False),
            field("chassis_number", "Chassis number", required=False),
            field("notes", "Notes", required=False),
        ]
        if kind == "bus-new":
            drivers = [("", "No assigned driver")] + [
                (str(r["employment_id"]), r["full_name"])
                for r in driver_service.get_available_driver_employments(today_lusaka())
            ]
            fields += [
                field("employment_id", "Driver", "select", drivers, required=False),
                field(
                    "status",
                    "Initial status",
                    "select",
                    [("ACTIVE", "Active"), ("INACTIVE", "Deactivated")],
                ),
            ]
            for document_type in sorted(bus_service.DOCUMENT_TYPES):
                for suffix, label, input_type in (
                    ("number", "Document number", "text"),
                    ("issue", "Issue date", "date"),
                    ("expiry", "Expiry date", "date"),
                ):
                    item = field(f"doc_{document_type}_{suffix}", label, input_type, required=False)
                    item["group"] = document_type.replace("_", " ").title()
                    fields.append(item)
        else:
            fields.append(
                field("route_effective_date", "Route effective date", "date", value=today)
            )
    elif kind == "bus-status":
        fields = [
            field(
                "status", "Status", "select", [("ACTIVE", "Active"), ("INACTIVE", "Deactivated")]
            ),
            field("effective_date", "Effective date", "date", value=today),
        ]
    elif kind == "route-new":
        fields = [field("name", "Route name"), field("description", "Description", required=False)]
    elif kind in {"driver-new", "driver-edit"}:
        fields = [
            field("full_name", "Driver name"),
            field("phone", "Phone number", "tel", required=False),
            field("address", "Address", required=False),
            field("next_of_kin_name", "Next of kin", required=False),
            field("next_of_kin_phone", "Next of kin phone", "tel", required=False),
            field("notes", "Notes", required=False),
        ]
        if kind == "driver-new":
            fields += [
                field("start_date", "Employment starts", "date", value=today),
                field("monthly_salary", "Monthly salary (K)", "money", value="2000"),
            ]
    elif kind == "account":
        fields = [field("opening_balance", "Starting balance (K)", "money")]
    elif kind == "rate":
        fields = [
            field(
                "rate_type", "Rate", "select", [("NORMAL_DAY", "Normal day"), ("SUNDAY", "Sunday")]
            ),
            field("amount", "Amount (K)", "money"),
            field("effective_from", "Effective from", "date", value=today),
        ]
    elif kind == "salary":
        drivers = [("", "Default salary")] + [
            (str(r["id"]), r["full_name"]) for r in driver_service.get_drivers_overview()
        ]
        fields = [
            field("driver_id", "Applies to", "select", drivers, required=False),
            field("monthly_salary", "Monthly salary (K)", "money"),
            field("effective_from", "Effective from", "date", value=today),
        ]
    elif kind == "advance":
        fields = [
            field(
                "amount",
                "Driver advance limit (K)",
                "money",
                value=str(preset_service.get_driver_advance_limit()),
            )
        ]
    elif kind == "reporting":
        fields = [
            field(
                "baseline_date",
                "Reporting baseline",
                "date",
                value=preset_service.get_reporting_baseline_date().isoformat(),
            )
        ]
    elif kind == "reminder":
        fields = [
            field(
                "preset_key",
                "Reminder",
                "select",
                [
                    ("MAINTENANCE_WARNING_DAYS", "Maintenance"),
                    ("DOCUMENT_EXPIRY_WARNING_DAYS", "Documents"),
                    ("OVERDUE_CASHING_WARNING_DAYS", "Overdue cashing"),
                ],
            ),
            field("warning_days", "Warning days", "number"),
            field("active", "Enabled", "checkbox", required=False, value=True),
        ]
    else:
        abort(404)
    for item in fields:
        if item["name"] in existing:
            item["value"] = existing[item["name"]] if existing[item["name"]] is not None else ""
    titles = {
        "bus-new": "Add bus",
        "bus-edit": "Edit bus",
        "bus-status": "Change bus status",
        "route-new": "Add route",
        "driver-new": "Add driver",
        "driver-edit": "Edit driver",
        "account": "Starting balance",
        "rate": "Cashing rate",
        "salary": "Salary preset",
        "advance": "Driver advance limit",
        "reporting": "Reporting baseline",
        "reminder": "Reminder preset",
    }
    return titles[kind], fields


def apply_operation(kind, record_id, data, reason):
    if any(len(v) > 500 for v in data.values()):
        raise ValueError("Keep each field to 500 characters or fewer.")
    limits = {
        "registration_number": 20,
        "name": 100,
        "model": 100,
        "chassis_number": 80,
        "full_name": 150,
        "phone": 30,
        "next_of_kin_name": 150,
        "next_of_kin_phone": 30,
    }
    if any(len(data.get(key, "")) > limit for key, limit in limits.items()):
        raise ValueError("One of the names or identifiers is too long.")
    if kind in {"bus-new", "bus-edit"}:
        route_id = positive_id(data, "route_id")
        if route_id not in {r["id"] for r in route_service.get_active_routes()}:
            raise ValueError("Choose an active route.")
        acquired = date_value(data, "date_acquired", optional=True)
        if acquired and acquired > today_lusaka():
            raise ValueError("Date acquired cannot be in the future.")
        values = {
            k: data.get(k)
            for k in ("registration_number", "model", "seating_capacity", "chassis_number", "notes")
        }
        values.update(route_id=route_id, date_acquired=acquired)
        if kind == "bus-new":
            documents = []
            for document_type in sorted(bus_service.DOCUMENT_TYPES):
                prefix = f"doc_{document_type}_"
                number = data.get(prefix + "number", "")
                issue = date_value(data, prefix + "issue", optional=True)
                expiry = date_value(data, prefix + "expiry", optional=True)
                if len(number) > 100 or (issue and expiry and expiry < issue):
                    raise ValueError("Check the document number and issue/expiry dates.")
                if number or issue or expiry:
                    documents.append(
                        {
                            "document_type": document_type,
                            "document_number": number,
                            "issue_date": issue,
                            "expiry_date": expiry,
                        }
                    )
            employment_id = positive_id(data, "employment_id", optional=True)
            if employment_id and employment_id not in {
                r["employment_id"]
                for r in driver_service.get_available_driver_employments(acquired or today_lusaka())
            }:
                raise ValueError("Choose an available driver for the acquired date.")
            return bus_service.create_bus(
                **values,
                status=data.get("status"),
                employment_id=employment_id,
                document_records=documents,
            )
        effective = date_value(data, "route_effective_date")
        if effective > today_lusaka():
            raise ValueError("Route changes cannot take effect in the future.")
        return bus_service.update_bus(record_id, **values, route_effective_date=effective)
    if kind == "bus-status":
        effective = date_value(data, "effective_date")
        if effective > today_lusaka():
            raise ValueError("Status changes cannot take effect in the future.")
        return bus_service.set_bus_status(record_id, data.get("status"), effective, reason)
    if kind == "route-new":
        return route_service.add_route(data.get("name", ""), data.get("description"))
    if kind in {"driver-new", "driver-edit"}:
        values = {
            k: data.get(k)
            for k in (
                "full_name",
                "phone",
                "address",
                "next_of_kin_name",
                "next_of_kin_phone",
                "notes",
            )
        }
        if kind == "driver-new":
            return driver_service.create_driver(
                **values,
                start_date=date_value(data, "start_date"),
                monthly_salary=money_value(data, "monthly_salary"),
            )
        return driver_service.update_driver(record_id, **values)
    if kind == "account":
        return account_service.update_opening_balance(
            record_id, money_value(data, "opening_balance")
        )
    if kind == "rate":
        return preset_service.set_cashing_rate(
            data.get("rate_type"),
            money_value(data, "amount"),
            date_value(data, "effective_from"),
            reason,
        )
    if kind == "salary":
        return preset_service.set_driver_salary_preset(
            money_value(data, "monthly_salary"),
            date_value(data, "effective_from"),
            positive_id(data, "driver_id", optional=True),
            reason,
        )
    if kind == "advance":
        return preset_service.set_driver_advance_limit(money_value(data, "amount"), reason)
    if kind == "reporting":
        preset_service.set_reporting_baseline_date(date_value(data, "baseline_date"), reason)
        return {"baseline_date": data["baseline_date"]}
    if kind == "reminder":
        days = data.get("warning_days", "")
        if not days.isdecimal() or int(days) > 3650:
            raise ValueError("Use a whole warning period from 0 to 3650 days.")
        return preset_service.set_reminder_preset(
            data.get("preset_key"), int(days), data.get("active") == "on", reason
        )
    raise ValueError("Unsupported operation.")


def save(kind, record_id, data, token, reason):
    writer = current_app.config.get("WRITE_DB_SETTINGS")
    if not writer:
        raise ValueError("The isolated write environment is not configured.")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValueError("Enter a reason of 1 to 500 characters.")
    action = f"{kind}:{record_id}"
    decoded = decode_token(token, action)
    operation = (
        (
            lambda: replace_schedule(
                data["pattern"], date.fromisoformat(data["effective_from"]), reason
            )
        )
        if kind == "schedule"
        else (lambda: apply_operation(kind, record_id, data, reason))
    )
    return execute_command(
        writer,
        current_app.config["OWNER_USERNAME"],
        decoded["key"],
        action,
        data,
        "reference-data",
        reason,
        lambda conn: snapshot(conn, TABLES[kind]),
        operation,
        decoded["version"],
    )


@bp.route("/manage/<kind>", defaults={"record_id": 0}, methods=["GET", "POST"])
@bp.route("/manage/<kind>/<int:record_id>", methods=["GET", "POST"])
@owner_required
def edit(kind, record_id):
    if kind not in TABLES or kind == "schedule":
        abort(404)
    try:
        title, fields = definition(kind, record_id)
    except ValueError:
        abort(404)
    with get_connection() as conn:
        state = snapshot(conn, TABLES[kind])
    token = (
        request.form.get("command_token", "")
        if request.method == "POST"
        else form_token(f"{kind}:{record_id}", state)
    )
    error, status = None, 200
    if request.method == "POST":
        data = {item["name"]: request.form.get(item["name"], "") for item in fields}
        try:
            save(kind, record_id, data, token, request.form.get("reason", ""))
        except CommandConflict as exc:
            error, status = str(exc), 409
        except ValueError as exc:
            error, status = str(exc), 400
        except (psycopg.IntegrityError, psycopg.DataError):
            error, status = "These details conflict with an existing record or its history.", 409
        else:
            flash("Saved.")
            target = (
                "home.buses"
                if kind.startswith("bus-")
                else (
                    "management.routes"
                    if kind == "route-new"
                    else "management.drivers"
                    if kind.startswith("driver-")
                    else "management.accounts"
                    if kind == "account"
                    else "management.presets"
                )
            )
            return redirect(url_for(target), code=303)
        for item in fields:
            item["value"] = (
                data[item["name"]] == "on" if item["type"] == "checkbox" else data[item["name"]]
            )
    return render_template(
        "manage_form.html",
        title=title,
        active="buses"
        if kind.startswith(("bus-", "driver-", "route-"))
        else "finance"
        if kind == "account"
        else "more",
        cancel_url=url_for(
            "home.buses"
            if kind.startswith("bus-")
            else "management.drivers"
            if kind.startswith("driver-")
            else "management.routes"
            if kind == "route-new"
            else "management.accounts"
            if kind == "account"
            else "management.presets"
        ),
        fields=fields,
        command_token=token,
        error=error,
        reason=request.form.get("reason", ""),
    ), status


@bp.get("/routes")
@owner_required
def routes():
    return render_template(
        "register.html",
        title="Routes",
        active="buses",
        kind="route-new",
        rows=route_service.get_all_routes(),
    )


@bp.get("/drivers")
@owner_required
def drivers():
    return render_template(
        "register.html",
        title="Drivers",
        active="buses",
        kind="driver-new",
        rows=driver_service.get_drivers_overview(),
    )


@bp.get("/buses/<int:bus_id>")
@owner_required
def bus_detail(bus_id):
    try:
        details = bus_service.get_bus_details(bus_id)
    except ValueError:
        abort(404)
    return render_template(
        "bus_detail.html", title=details["bus"]["registration_number"], active="buses", **details
    )


@bp.get("/accounts")
@owner_required
def accounts():
    return render_template(
        "accounts.html",
        title="Accounts",
        active="finance",
        accounts=account_service.get_accounts_for_management(),
    )


@bp.get("/presets")
@owner_required
def presets():
    return render_template(
        "presets.html",
        title="Business Presets",
        active="more",
        rates=preset_service.list_cashing_rates(),
        salaries=preset_service.list_driver_salary_presets(),
        reminders=preset_service.list_reminder_presets(),
        settings=preset_service.get_business_settings(),
    )


@bp.route("/presets/schedule", methods=["GET", "POST"])
@owner_required
def schedule():
    rules = preset_service.list_cashing_schedule_rules()
    with get_connection() as conn:
        state = snapshot(conn, TABLES["schedule"])
    token = (
        request.form.get("command_token", "")
        if request.method == "POST"
        else form_token("schedule:0", state)
    )
    values = {r["collection_day"]: r for r in rules if r["effective_to"] is None}
    effective = request.form.get("effective_from", today_lusaka().isoformat())
    error, status = None, 200
    if request.method == "POST":
        try:
            pattern = [
                {
                    "collection_day": day,
                    "covered_days": [int(v) for v in request.form.getlist(f"covered_{day}")],
                    "include_previous_sunday": request.form.get(f"sunday_{day}") == "on",
                }
                for day in range(1, 8)
                if request.form.get(f"enabled_{day}") == "on"
            ]
            values = {r["collection_day"]: r for r in pattern}
            save(
                "schedule",
                0,
                {"pattern": pattern, "effective_from": effective},
                token,
                request.form.get("reason", ""),
            )
        except CommandConflict as exc:
            error, status = str(exc), 409
        except (ValueError, psycopg.IntegrityError) as exc:
            error, status = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Schedule conflicts with stored history.",
                400,
            )
        else:
            flash("Schedule saved.")
            return redirect(url_for("management.schedule"), code=303)
    return render_template(
        "schedule.html",
        title="Collection Schedule",
        active="more",
        days=DAY_NAMES,
        rules=rules,
        values=values,
        effective=effective,
        command_token=token,
        error=error,
        reason=request.form.get("reason", ""),
    ), status


@bp.get("/presets/schedule/coverage")
@owner_required
def coverage():
    try:
        on_date = date.fromisoformat(request.args.get("date", ""))
        result = get_scheduled_coverage(on_date)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    return {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in result.items()
    }
