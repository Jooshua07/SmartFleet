"""Complete cashing invoices: all eligible buses, explicit exceptions only."""

from datetime import timedelta
from decimal import Decimal

import psycopg
from flask import current_app, flash, redirect, render_template, request, url_for

from database.connection import shared_transaction
from services import bus_service, preset_service
from services import smart_cashing_service as cashing
from smartfleet_web.commands import form_token
from smartfleet_web.management import money_value
from smartfleet_web.recording import (
    airtel_account_id,
    cashing_preview,
    checked_date,
    command,
    safe_error,
    state,
)
from utils.dates import today_lusaka


def complete_allocations(data, preview):
    mode = data.get("mode", "STANDARD")
    if mode not in {"STANDARD", "ADJUSTED"}:
        raise ValueError("Choose Standard or Adjusted Buses.")
    if not preview["buses"]:
        raise ValueError(
            "No buses were active during this collection's coverage. Check the date and bus history."
        )
    available = {str(b["id"]): b for b in preview["buses"]}
    selected = data.get("adjust_ids", []) if mode == "ADJUSTED" else []
    if len(selected) != len(set(selected)) or any(bid not in available for bid in selected):
        raise ValueError("Choose different eligible buses to adjust.")
    standard = cashing.build_standard_allocations(
        preview, [b["id"] for b in preview["buses"]], [], preview["expected_total"]
    )
    entries = standard["entries"]
    for entry in entries:
        bid = str(entry["bus_id"])
        if bid not in selected:
            continue
        bus = available[bid]
        days_text = data.get(f"days_{bid}", str(bus["normal_days"]))
        if not days_text.isdecimal() or not 0 <= int(days_text) <= bus["normal_days"]:
            raise ValueError("Worked days must not exceed historically active days.")
        days = int(days_text)
        add_sunday = data.get(f"sunday_{bid}") == "on"
        if add_sunday:
            sunday_date = preview.get("previous_sunday")
            if not sunday_date or not bus_service.get_bus_active_day_counts(
                sunday_date, sunday_date, [bus["id"]]
            ).get(bus["id"]):
                raise ValueError("Sunday is not eligible for this bus/date.")
        actual = money_value(data, f"amount_{bid}")
        sunday = money_value(data, f"sunday_amount_{bid}") if add_sunday else Decimal("0")
        expected = days * bus["normal_daily_rate"] + (bus["sunday_rate"] if add_sunday else 0)
        classification = data.get(f"classification_{bid}", "MATCHED")
        explanation = data.get(f"explanation_{bid}", "").strip()
        changed_days = days != bus["normal_days"]
        difference = actual + sunday - expected
        if (difference or changed_days) and not explanation:
            raise ValueError("Enter a reason for the adjusted amount or worked days.")
        if classification not in cashing.DIFFERENCE_CLASSIFICATIONS:
            raise ValueError("Choose a valid difference classification.")
        if difference and classification == "MATCHED":
            raise ValueError("Choose a classification for the difference.")
        if (
            not difference
            and classification != "MATCHED"
            and not (changed_days and classification == "REDUCED_WORKDAYS")
        ):
            raise ValueError("A matching amount must use Matched.")
        if difference > 0 and classification != "SURPLUS":
            raise ValueError("An amount above expected must use Surplus.")
        if difference < 0 and classification == "SURPLUS":
            raise ValueError("A shortfall cannot be classified as Surplus.")
        entry.update(
            normal_days=days,
            sunday_days=int(add_sunday),
            sunday_worked=add_sunday,
            actual_amount=actual + sunday,
            difference_classification=classification,
            allocation_provenance="MANUAL_ADJUSTMENT",
            worked_days_adjusted=changed_days,
            explanation=explanation,
        )
        if classification == "CONFIRMED_UNPAID_OBLIGATION":
            if difference >= 0:
                raise ValueError("An unpaid obligation needs a shortfall.")
            entry["obligation"] = {
                "amount": -difference,
                "responsible_party_type": "OTHER",
                "responsible_party_name": data.get(f"responsible_{bid}", ""),
            }
    total = sum((entry["actual_amount"] for entry in entries), Decimal("0"))
    if total >= Decimal("1000000000"):
        raise ValueError("The collection total exceeds the supported amount.")
    return dict(
        entries=entries,
        total_received=total,
        unallocated_amount=Decimal("0"),
        difference_classification="MATCHED"
        if all(e["difference_classification"] == "MATCHED" for e in entries)
        else "UNKNOWN_DIFFERENCE",
    )


def complete_collection():
    data = dict(
        collection_date=request.args.get("date", today_lusaka().isoformat()),
        mode="STANDARD",
        notes="",
        adjust_ids=[],
    )
    if request.method == "GET" and not request.args.get("date"):
        rules = preset_service.list_cashing_schedule_rules()
        for offset in range(7):
            candidate = today_lusaka() - timedelta(days=offset)
            try:
                cashing.get_collection_coverage(candidate, schedule_rules=rules)
                data["collection_date"] = candidate.isoformat()
                break
            except ValueError:
                continue
    if request.method == "POST":
        data = {name: request.form.get(name, "") for name in ("collection_date", "mode", "notes")}
        data["adjust_ids"] = (
            request.form.getlist("adjust_ids") if data["mode"] == "ADJUSTED" else []
        )
        for bid in data["adjust_ids"]:
            if not bid.isdecimal() or len(bid) > 10:
                data["adjust_ids"] = ["invalid"]
                break
            for prefix in (
                "amount",
                "days",
                "sunday",
                "sunday_amount",
                "classification",
                "explanation",
                "responsible",
            ):
                key = f"{prefix}_{bid}"
                if key in request.form:
                    data[key] = request.form[key]
    error, status, preview, token = None, 200, None, request.form.get("command_token", "")
    try:
        if any(len(str(value)) > 500 for value in data.values()):
            raise ValueError("Keep each field within 500 characters.")
        on_date = checked_date(data, "collection_date")
        action = "complete-cashing:" + on_date.isoformat()
        with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            preview, _ = cashing_preview(on_date)
            if request.method == "GET":
                token = form_token(action, state(connection))
        if request.method == "POST":

            def save():
                fresh, rules = cashing_preview(on_date)
                allocation = complete_allocations(data, fresh)
                return cashing.record_smart_cashing_collection(
                    on_date,
                    airtel_account_id(),
                    **allocation,
                    cashing_mode=data["mode"],
                    notes=data["notes"],
                    schedule_rules=rules,
                )

            result = command(
                action,
                data,
                token,
                save,
                reason="Record full expected cashing"
                if data["mode"] == "STANDARD"
                else "Record cashing with explicit bus adjustments",
            )
            flash("Cashing saved.", "success")
            return redirect(url_for("recording.receipt", record_id=result["id"]), code=303)
    except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
        error, status = safe_error(exc)
    return render_template(
        "complete_cashing.html",
        title="Record Cashing",
        active="finance",
        data=data,
        preview=preview,
        command_token=token,
        error=error,
        classifications=sorted(cashing.DIFFERENCE_CLASSIFICATIONS),
    ), status
