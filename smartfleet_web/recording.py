"""Audited financial recording. All calculations and commits are server-authoritative."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

import psycopg
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from psycopg.rows import dict_row

from database.connection import get_connection, shared_transaction
from services import bus_service, cashing_service, expense_service, preset_service
from services import smart_cashing_service as cashing
from smartfleet_web.auth import owner_required
from smartfleet_web.commands import CommandConflict, decode_token, execute_command, form_token
from smartfleet_web.management import date_value, field, money_value, positive_id, snapshot
from utils.dates import today_lusaka

bp = Blueprint("recording", __name__)
FINANCIAL_TABLES = (
    "expenses",
    "expense_allocations",
    "financial_transactions",
    "remittance_collections",
    "remittances",
    "cashing_obligations",
    "cashing_obligation_payments",
)
COMMAND_TABLES = (
    *FINANCIAL_TABLES,
    "cashing_rates",
    "cashing_schedule_rules",
    "bus_status_history",
    "financial_accounts",
    "business_settings",
)


def state(connection):
    return snapshot(connection, COMMAND_TABLES)


def airtel_account_id():
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM financial_accounts WHERE active AND account_type='AIRTEL_MONEY' ORDER BY id LIMIT 1"
        ).fetchone()
    if row is None:
        raise ValueError("No active Airtel Money account is configured.")
    return row[0]


def token_for(action):
    if request.method == "POST":
        return request.form.get("command_token", "")
    with get_connection() as connection:
        return form_token(action, state(connection))


def command(action, payload, token, operation, reason=None):
    decoded = decode_token(token, action)
    reason = request.form.get("reason", "").strip() if reason is None else reason
    if not reason or len(reason) > 500:
        raise ValueError("Enter a reason of 1 to 500 characters.")
    if not current_app.config.get("WRITE_DB_SETTINGS"):
        raise ValueError("The isolated recording environment is not configured.")
    return execute_command(
        current_app.config["WRITE_DB_SETTINGS"],
        current_app.config["OWNER_USERNAME"],
        decoded["key"],
        action,
        payload,
        "reference-data",
        reason,
        state,
        operation,
        decoded["version"],
    )


def checked_date(data, name):
    value = date_value(data, name)
    if value > today_lusaka():
        raise ValueError("Recording dates cannot be in the future.")
    return value


def safe_error(error):
    if isinstance(error, CommandConflict):
        return str(error), 409
    if isinstance(error, ValueError):
        return str(error), 400
    return "These details conflict with a record or its linked financial history.", 409


@bp.get("/expenses")
@bp.get("/collections")
@owner_required
def history():
    is_expense = request.path == "/expenses"
    try:
        page = int(request.args.get("page", "1"))
        if not 1 <= page <= 10000:
            raise ValueError
    except ValueError:
        abort(400)
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            query = (
                "SELECT e.*,ec.name AS label FROM expenses e JOIN expense_categories ec ON ec.id=e.category_id "
                "ORDER BY expense_date DESC,e.id DESC LIMIT 21 OFFSET %s"
                if is_expense
                else "SELECT * FROM remittance_collections ORDER BY collection_date DESC,id DESC LIMIT 21 OFFSET %s"
            )
            cursor.execute(query, ((page - 1) * 20,))
            rows = cursor.fetchall()
    return render_template(
        "record_history.html",
        title="Expenses" if is_expense else "Collections",
        active="finance",
        rows=rows[:20],
        page=page,
        has_next=len(rows) > 20,
        is_expense=is_expense,
    )


@bp.route("/record-expense", defaults={"record_id": 0}, methods=["GET", "POST"])
@bp.route("/expenses/<int:record_id>/edit", methods=["GET", "POST"])
@owner_required
def expense(record_id):
    existing = {}
    if record_id:
        try:
            existing = expense_service.get_expense(record_id)
        except ValueError:
            abort(404)
    categories = expense_service.get_operating_expense_categories()
    groups = {
        "Maintenance": "Bus",
        "Parts": "Bus",
        "Transfer Fees": "Finance",
        "Office & Administration": "Admin",
    }
    buses = bus_service.get_all_buses(limit=100)
    fields = [
        field("expense_date", "Expense date", "date", value=today_lusaka().isoformat()),
        field(
            "category_id",
            "Category",
            "select",
            [
                (str(r["id"]), groups.get(r["name"], "Other") + " - " + r["name"])
                for r in categories
            ],
        ),
        field(
            "scope",
            "Expense scope",
            "select",
            [("GENERAL", "General business"), ("BUS", "Specific bus")],
        ),
        field(
            "bus_id",
            "Bus",
            "select",
            [("", "No bus")] + [(str(r["id"]), r["registration_number"]) for r in buses],
            required=False,
        ),
        field("amount", "Amount (K)", "money"),
        field("description", "Expense title"),
        field("vendor_name", "Paid to", required=False),
        field("reference_number", "Receipt/reference", required=False),
        field("notes", "Notes", required=False),
    ]
    action = f"expense:{record_id}"
    token, error, status = token_for(action), None, 200
    data = {f["name"]: request.form.get(f["name"], "") for f in fields}
    if request.method == "POST":

        def save():
            amount = money_value(data, "amount")
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
            if any(
                len(data.get(k, "")) > limit
                for k, limit in (("vendor_name", 150), ("reference_number", 100), ("notes", 500))
            ):
                raise ValueError("Check the length of the vendor, reference or notes.")
            values = dict(
                expense_date=checked_date(data, "expense_date"),
                category_id=positive_id(data, "category_id"),
                amount=amount,
                description=data["description"],
                financial_account_id=airtel_account_id(),
                scope=data["scope"],
                bus_id=positive_id(data, "bus_id") if data["scope"] == "BUS" else None,
                vendor_name=data["vendor_name"],
                reference_number=data["reference_number"],
                notes=data["notes"],
            )
            return (
                expense_service.update_business_expense(record_id, **values)
                if record_id
                else expense_service.record_business_expense(**values)
            )

        try:
            command(action, data, token, save)
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
        else:
            flash("Expense saved.")
            return redirect(url_for("recording.expense"), code=303)
    for item in fields:
        if request.method == "POST":
            item["value"] = data[item["name"]]
        elif item["name"] in existing:
            item["value"] = existing[item["name"]] if existing[item["name"]] is not None else ""
    return render_template(
        "expense_form.html",
        title="Edit expense" if record_id else "Record Expense",
        active="finance",
        fields=fields,
        command_token=token,
        error=error,
        reason=request.form.get("reason", ""),
        cancel_url="/expenses",
        expense_scope=data.get("scope", "GENERAL")
        if request.method == "POST"
        else existing.get("scope", request.args.get("scope", "GENERAL")),
    ), status


def cashing_preview(on_date):
    rules = preset_service.list_cashing_schedule_rules()
    return cashing.get_smart_cashing_preview(on_date, schedule_rules=rules), rules


def allocations(data, preview, direct=False):
    selected = data.get("bus_ids", [])
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("Choose one or more different buses.")
    available = {str(b["id"]): b for b in preview["buses"]}
    if any(bus_id not in available for bus_id in selected):
        raise ValueError("Choose eligible buses for this collection date.")
    sunday_ids = []
    entries = []
    actual_total = Decimal("0")
    for bus_id in selected:
        bus = available[bus_id]
        add_sunday = data.get(f"sunday_{bus_id}") == "on"
        if not direct and not bus["normal_days"] and not add_sunday:
            raise ValueError("This bus is eligible only for its previous Sunday work.")
        if add_sunday and not direct:
            if not preview.get("previous_sunday") or not bus_service.get_bus_active_day_counts(
                preview["previous_sunday"], preview["previous_sunday"], [bus["id"]]
            ).get(bus["id"]):
                raise ValueError("Sunday is not eligible for this bus/date.")
        sunday = money_value(data, f"sunday_amount_{bus_id}") if add_sunday else Decimal("0")
        if add_sunday:
            sunday_ids.append(bus["id"])
        if data.get("mode") == "STANDARD" and not direct:
            if add_sunday and sunday != bus["sunday_rate"]:
                raise ValueError("Use Adjust buses for a Sunday amount different from the preset.")
            continue
        actual = money_value(
            data, "common_amount" if data.get("same_amount") == "on" else f"amount_{bus_id}"
        )
        actual_total += actual + sunday
        if direct:
            entries.append(
                {
                    "include": True,
                    "bus_id": bus["id"],
                    "normal_amount": actual,
                    "sunday_amount": sunday,
                }
            )
            continue
        days_text = data.get(f"days_{bus_id}", "")
        if not days_text.isdecimal() or not 0 <= int(days_text) <= bus["normal_days"]:
            raise ValueError("Worked days must not exceed historically active days.")
        days = int(days_text)
        expected = days * bus["normal_daily_rate"] + (bus["sunday_rate"] if add_sunday else 0)
        classification = data.get(f"classification_{bus_id}") or "MATCHED"
        explanation = data.get(f"explanation_{bus_id}", "").strip()
        if (expected != actual + sunday or days != bus["normal_days"]) and not explanation:
            raise ValueError("Enter a reason when an amount or worked days differ.")
        if (
            expected == actual + sunday
            and classification != "MATCHED"
            and not (days != bus["normal_days"] and classification == "REDUCED_WORKDAYS")
        ):
            raise ValueError("A matching amount must use Matched.")
        if expected != actual + sunday and classification == "MATCHED":
            raise ValueError("Choose a classification for the difference.")
        entry = dict(
            bus_id=bus["id"],
            normal_days=days,
            normal_daily_rate=bus["normal_daily_rate"],
            sunday_days=int(add_sunday),
            sunday_rate=bus["sunday_rate"],
            actual_amount=actual + sunday,
            difference_classification=classification,
            allocation_provenance="MANUAL_ADJUSTMENT",
            worked_days_adjusted=days != bus["normal_days"],
            explanation=explanation,
        )
        if classification == "CONFIRMED_UNPAID_OBLIGATION":
            if expected <= actual + sunday:
                raise ValueError("An unpaid obligation needs a shortfall.")
            entry["obligation"] = {
                "amount": expected - actual - sunday,
                "responsible_party_type": "OTHER",
                "responsible_party_name": data.get(f"responsible_{bus_id}", ""),
            }
        entries.append(entry)
    if data.get("mode") == "STANDARD" and not direct:
        result = cashing.build_standard_allocations(
            preview,
            [int(v) for v in selected],
            sunday_ids,
            money_value(data, "total_received"),
            data.get("classification"),
        )
        if data.get("classification") == "CONFIRMED_UNPAID_OBLIGATION":
            raise ValueError("Use Adjust buses to assign a confirmed unpaid obligation.")
        result.pop("expected_total")
        result["total_received"] = money_value(data, "total_received")
        return result
    try:
        unallocated = (
            Decimal(data.get("unallocated_amount", "0") or "0") if not direct else Decimal("0")
        )
    except InvalidOperation:
        raise ValueError("Enter a valid unallocated amount.") from None
    if (
        not unallocated.is_finite()
        or abs(unallocated) >= 1000000000
        or unallocated.as_tuple().exponent < -2
        or actual_total + unallocated < 0
    ):
        raise ValueError("Check the unallocated amount and total receipt.")
    return {
        "entries": entries,
        "total_received": actual_total + unallocated,
        "unallocated_amount": unallocated,
        "difference_classification": "MATCHED"
        if unallocated == 0
        and all(e.get("difference_classification", "MATCHED") == "MATCHED" for e in entries)
        else "UNKNOWN_DIFFERENCE",
    }


@bp.route("/record-cashing", defaults={"record_id": 0}, methods=["GET", "POST"])
@bp.route("/collections/<int:record_id>/edit", methods=["GET", "POST"])
@owner_required
def collection(record_id):
    if not record_id:
        from smartfleet_web.cashing_entry import complete_collection

        return complete_collection()
    existing = None
    if record_id:
        try:
            existing = cashing_service.get_cashing_collection(record_id)
        except ValueError:
            abort(404)
    direct = bool(existing and existing["collection"]["cashing_mode"] == "DIRECT")
    initial = (
        existing["collection"]["collection_date"].isoformat()
        if existing
        else today_lusaka().isoformat()
    )
    if not existing and not request.args.get("date") and request.method == "GET":
        effective_rules = preset_service.list_cashing_schedule_rules()
        for offset in range(7):
            candidate = today_lusaka() - timedelta(days=offset)
            try:
                cashing.get_collection_coverage(candidate, schedule_rules=effective_rules)
            except ValueError:
                continue
            initial = candidate.isoformat()
            break
    data = (
        request.form.to_dict()
        if request.method == "POST"
        else {
            "collection_date": request.args.get("date", initial),
            "mode": existing["collection"]["cashing_mode"] if existing else "STANDARD",
        }
    )
    data["bus_ids"] = (
        request.form.getlist("bus_ids")
        if request.method == "POST"
        else [str(e["bus_id"]) for e in existing["entries"]]
        if existing
        else []
    )
    # Transport tokens vary across owner sessions and are not part of the financial intent.
    data.pop("csrf_token", None)
    data.pop("command_token", None)
    data.pop("financial_account_id", None)
    action, error, status = f"collection:{record_id}", None, 200
    token = token_for(action)
    preview, rules = None, []
    try:
        on_date = checked_date(data, "collection_date")
        if direct:
            preview = {
                "buses": [
                    {
                        **b,
                        "normal_days": 1,
                        "normal_daily_rate": Decimal("0"),
                        "sunday_rate": Decimal("0"),
                    }
                    for b in bus_service.get_all_buses(limit=100)
                ],
                "previous_sunday": None,
            }
        else:
            preview, rules = cashing_preview(on_date)
        if request.method == "GET" and existing:
            data["total_received"] = str(existing["collection"]["total_amount"])
            data["unallocated_amount"] = str(existing["collection"]["unallocated_amount"])
            data["notes"] = existing["collection"]["notes"] or ""
            for entry in existing["entries"]:
                bid = entry["bus_id"]
                data.update(
                    {
                        f"amount_{bid}": str(
                            entry["actual_amount"] - entry["sunday_days"] * entry["sunday_rate"]
                        ),
                        f"days_{bid}": str(entry["normal_days"]),
                        f"sunday_{bid}": "on" if entry["sunday_days"] else "",
                        f"sunday_amount_{bid}": str(entry["sunday_days"] * entry["sunday_rate"]),
                        f"classification_{bid}": entry["difference_classification"],
                        f"explanation_{bid}": entry["explanation"] or "",
                    }
                )
        if request.method == "POST":

            def save():
                fresh, effective_rules = (preview, rules) if direct else cashing_preview(on_date)
                allocation = allocations(data, fresh, direct)
                account_id = airtel_account_id()
                if direct:
                    return cashing_service.update_direct_cashing_collection(
                        record_id, on_date, account_id, allocation["entries"], data.get("notes")
                    )
                mode = data.get("mode")
                if mode not in {"STANDARD", "ADJUSTED"}:
                    raise ValueError("Choose Standard or Adjust buses.")
                values = dict(
                    collection_date=on_date,
                    financial_account_id=account_id,
                    **allocation,
                    cashing_mode=mode,
                    notes=data.get("notes"),
                    schedule_rules=effective_rules,
                )
                return (
                    cashing.update_smart_cashing_collection(record_id, **values)
                    if record_id
                    else cashing.record_smart_cashing_collection(**values)
                )

            command(action, data, token, save)
            flash("Cashing saved.")
            return redirect(url_for("recording.collection", date=on_date.isoformat()), code=303)
    except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
        error, status = safe_error(exc)
    return render_template(
        "record_cashing.html",
        title="Edit cashing" if record_id else "Record Cashing",
        active="finance",
        preview=preview,
        data=data,
        command_token=token,
        error=error,
        direct=direct,
        classifications=sorted(cashing.DIFFERENCE_CLASSIFICATIONS),
    ), status if request.method == "POST" else 200


@bp.get("/collections/<int:record_id>/receipt")
@owner_required
def receipt(record_id):
    try:
        with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            saved = cashing_service.get_cashing_collection(record_id)
    except ValueError:
        abort(404)
    return render_template(
        "cashing_receipt.html", title="Recorded Cashing", active="finance", **saved
    )


@bp.route("/delete/<kind>/<int:record_id>", methods=["GET", "POST"])
@owner_required
def delete(kind, record_id):
    if kind not in {"expense", "collection"}:
        abort(404)
    action = f"delete-{kind}:{record_id}"
    token, error, status = token_for(action), None, 200
    if request.method == "POST":
        try:
            if request.form.get("confirm") != "on":
                raise ValueError("Confirm deletion before continuing.")

            def remove():
                if kind == "expense":
                    expense_service.delete_business_expense(record_id)
                else:
                    cashing_service.delete_cashing_collection(record_id)
                return {"deleted": record_id}

            command(action, {"kind": kind, "id": record_id, "confirm": "on"}, token, remove)
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
        else:
            flash("Record deleted.")
            return redirect("/expenses" if kind == "expense" else "/collections", code=303)
    return render_template(
        "confirm_delete.html",
        title="Delete record",
        active="finance",
        command_token=token,
        error=error,
    ), status


@bp.get("/obligations")
@owner_required
def obligations():
    return render_template(
        "obligations.html",
        title="Unpaid obligations",
        active="finance",
        rows=cashing.list_open_cashing_obligations(100),
    )


@bp.route("/obligations/<int:record_id>", methods=["GET", "POST"])
@owner_required
def payment(record_id):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM cashing_obligations WHERE id=%s", (record_id,))
            obligation = cursor.fetchone()
    if obligation is None:
        abort(404)
    fields = [
        field("payment_date", "Payment date", "date", value=today_lusaka().isoformat()),
        field("amount", "Amount (K)", "money"),
        field(
            "financial_account_id",
            "Paid into",
            "select",
            [
                (str(r["id"]), r["name"])
                for r in cashing_service.get_active_financial_accounts()
                if r["account_type"] == "AIRTEL_MONEY"
            ],
        ),
    ]
    action = f"settlement:{record_id}"
    token, error, status = token_for(action), None, 200
    data = {f["name"]: request.form.get(f["name"], "") for f in fields}
    if request.method == "POST":
        try:

            def pay():
                payment_date = checked_date(data, "payment_date")
                if payment_date < obligation["recognized_date"]:
                    raise ValueError("Payment cannot precede the obligation.")
                return cashing.record_obligation_payment(
                    record_id,
                    payment_date,
                    money_value(data, "amount"),
                    positive_id(data, "financial_account_id"),
                    request.form.get("reason"),
                )

            command(action, data, token, pay)
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
        else:
            flash("Settlement saved.")
            return redirect(url_for("recording.payment", record_id=record_id), code=303)
        for item in fields:
            item["value"] = data[item["name"]]
    return render_template(
        "settlement.html",
        title="Settle obligation",
        active="finance",
        fields=fields,
        command_token=token,
        error=error,
        reason=request.form.get("reason", ""),
        cancel_url=url_for("recording.obligations"),
        obligation=obligation,
        payments=cashing.list_cashing_obligation_payments(record_id),
    ), status
