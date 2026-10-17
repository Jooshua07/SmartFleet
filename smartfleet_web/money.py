"""Owner-authorized payroll, loans and owner money using existing audited services."""

import psycopg
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request

from database.connection import get_connection, shared_transaction
from services import driver_money_service as payroll
from services import loan_service as loans
from smartfleet_web.auth import owner_required
from smartfleet_web.commands import decode_token, execute_command, form_token
from smartfleet_web.management import field, money_value, positive_id, snapshot
from smartfleet_web.recording import COMMAND_TABLES, airtel_account_id, checked_date, safe_error
from utils.dates import today_lusaka

bp = Blueprint("money", __name__)
MONEY_TABLES = (
    "driver_advances",
    "driver_salaries",
    "salary_advance_recoveries",
    "salary_deduction_allocations",
    "driver_deductions",
    "business_loans",
    "loan_repayments",
    "owner_loans",
    "owner_loan_transactions",
    "correction_audit",
    "driver_employments",
    "driver_assignments",
    "driver_salary_presets",
    "drivers",
)
ACTIONS = {
    "advance": "Record Driver Advance",
    "salary": "Record Driver Salary",
    "loan": "Add Loan",
    "repayment": "Record Loan Repayment",
    "owner-pays-loan": "Owner Pays Business Loan",
    "owner-funding": "Owner Loan to Business",
    "owner-drawing": "Owner Drawing",
    "owner-repayment": "Business Repays Owner",
    "reclassify-salary": "Correct Expense to Salary",
    "reclassify-loan": "Correct Expense to Loan Repayment",
    "associate": "Identify Loan Repayment",
}
CANCELLATIONS = {
    "advance": payroll.cancel_driver_advance,
    "salary": payroll.cancel_driver_salary,
    "repayment": loans.cancel_loan_repayment,
    "owner": loans.cancel_owner_loan_transaction,
    "drawing": loans.cancel_owner_drawing,
}


def state(connection):
    return snapshot(connection, tuple(dict.fromkeys((*COMMAND_TABLES, *MONEY_TABLES))))


def command_token(action):
    if request.method == "POST":
        return request.form.get("command_token", "")
    with get_connection() as connection:
        return form_token(action, state(connection))


def command(action, data, token, operation):
    decoded = decode_token(token, action)
    reason = request.form.get("reason", "").strip()
    if not reason or len(reason) > 500:
        raise ValueError("Enter a reason of 1 to 500 characters.")
    if any(len(str(value)) > 500 for value in data.values()):
        raise ValueError("Keep each field within 500 characters.")
    if not current_app.config.get("WRITE_DB_SETTINGS"):
        raise ValueError("The isolated financial environment is not configured.")
    return execute_command(
        current_app.config["WRITE_DB_SETTINGS"],
        current_app.config["OWNER_USERNAME"],
        decoded["key"],
        action,
        data,
        "reference-data",
        reason,
        state,
        operation,
        decoded["version"],
    )


def salary_period(data):
    try:
        year, month = int(data["salary_year"]), int(data["salary_month"])
        from datetime import date

        start = date(year, month, 1)
    except (ValueError, KeyError, OverflowError):
        raise ValueError("Enter a valid salary month and year.") from None
    if year < 2000 or start > today_lusaka():
        raise ValueError("Choose a salary month from 2000 through the current month.")
    return year, month


def definition(action):
    today = today_lusaka()
    fields = []
    if action in {"advance", "salary", "reclassify-salary"}:
        fields.append(
            field(
                "employment_id",
                "Driver employment",
                "select",
                [
                    (str(r["employment_id"]), f"{r['driver_name']} | {r['start_date']}")
                    for r in payroll.list_driver_money_profiles()
                ],
            )
        )
    if action.startswith("reclassify"):
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT e.id,e.description,e.amount FROM expenses e JOIN financial_transactions ft ON ft.id=e.financial_transaction_id WHERE ft.transaction_type='EXPENSE' ORDER BY e.expense_date DESC,e.id DESC LIMIT 100"
            ).fetchall()
        fields.append(
            field(
                "expense_id",
                "Original expense",
                "select",
                [(str(r[0]), f"{r[1]} | K {r[2]} | #{r[0]}") for r in rows],
            )
        )
    if action in {"salary", "reclassify-salary"}:
        fields.extend(
            [
                field("salary_year", "Salary year", "number", value=today.year),
                field(
                    "salary_month",
                    "Salary month",
                    "select",
                    [(str(m), str(m)) for m in range(1, 13)],
                    value=today.month,
                ),
            ]
        )
    if action == "salary":
        fields.extend(
            [
                field("recovery_amount", "Advance recovery (K)", "money", required=False),
                field("other_deductions", "Other deductions (K)", "money", value="0"),
            ]
        )
    if action == "loan":
        fields.extend(
            [
                field("loan_name", "Loan name"),
                field("lender", "Lender/company/association"),
                field("original_amount", "Original principal (K)", "money"),
                field("default_monthly_repayment", "Known repayment (K)", "money", required=False),
                field("term_months", "Term in months", "number", required=False),
            ]
        )
    if action in {"repayment", "owner-pays-loan", "reclassify-loan", "associate"}:
        fields.append(
            field(
                "loan_id",
                "Loan",
                "select",
                ([] if action == "associate" else [("", "Unidentified loan")])
                + [
                    (
                        str(r["id"]),
                        f"{r['loan_name']} | {r['lender']} | K {r['outstanding_principal']} left",
                    )
                    for r in loans.list_business_loans()
                    if r["status"] == "ACTIVE"
                ],
                required=action == "associate",
            )
        )
    if action == "associate":
        fields.append(
            field(
                "repayment_id",
                "Unidentified repayment",
                "select",
                [
                    (str(r["id"]), f"{r['repayment_date']} | K {r['amount']} | #{r['id']}")
                    for r in loans.list_loan_repayments(100)
                    if r["loan_id"] is None
                ],
            )
        )
    if action in {"repayment", "owner-pays-loan"}:
        if action == "repayment":
            fields.append(
                field(
                    "payment_source",
                    "Payment source",
                    "select",
                    [
                        ("BUSINESS_ACCOUNT", "Business funds"),
                        ("OWNER_PERSONAL", "Owner personal funds"),
                    ],
                )
            )
        fields.extend(
            [
                field("principal_amount", "Principal paid (K)", "money"),
                field("interest_or_fees", "Interest/fees (K)", "money", value="0"),
                field("paid_to", "Paid to", required=False),
                field("reference", "Reference", required=False),
            ]
        )
    if action in {"advance", "owner-funding", "owner-drawing", "owner-repayment"}:
        fields.append(field("amount", "Amount (K)", "money"))
    if action == "owner-drawing":
        fields.append(field("reference", "Reference", required=False))
    if action not in {"associate", "reclassify-loan", "reclassify-salary"}:
        fields.append(field("date", "Date", "date", value=today.isoformat()))
    fields.append(field("notes", "Notes", required=False))
    return fields


def apply_operation(action, data):
    notes = data.get("notes")
    if action == "loan":
        return loans.add_business_loan(
            data["loan_name"],
            data["lender"],
            money_value(data, "original_amount"),
            checked_date(data, "date"),
            data["default_monthly_repayment"] or None,
            data["term_months"] or None,
            notes,
        )
    if action == "associate":
        return loans.associate_loan_repayment(
            positive_id(data, "repayment_id"), positive_id(data, "loan_id")
        )
    if action == "reclassify-loan":
        return loans.reclassify_expense_as_loan_repayment(
            positive_id(data, "expense_id"),
            positive_id(data, "loan_id", optional=True),
            notes=notes,
        )
    if action in {"salary", "reclassify-salary"}:
        year, month = salary_period(data)
        employment = positive_id(data, "employment_id")
        if action == "reclassify-salary":
            return payroll.reclassify_expense_as_driver_salary(
                positive_id(data, "expense_id"), employment, year, month, notes
            )
        return payroll.record_driver_salary(
            employment,
            year,
            month,
            checked_date(data, "date"),
            recovery_amount=None
            if not data["recovery_amount"]
            else money_value(data, "recovery_amount"),
            other_deductions=money_value(data, "other_deductions"),
            notes=notes,
            financial_account_id=airtel_account_id(),
        )
    day = checked_date(data, "date")
    if action == "advance":
        return payroll.record_driver_advance(
            positive_id(data, "employment_id"),
            day,
            money_value(data, "amount"),
            request.form.get("reason"),
            notes,
            airtel_account_id(),
        )
    if action in {"repayment", "owner-pays-loan"}:
        source = "OWNER_PERSONAL" if action == "owner-pays-loan" else data["payment_source"]
        return loans.record_loan_repayment(
            day,
            money_value(data, "principal_amount"),
            source,
            loan_id=positive_id(data, "loan_id", optional=True),
            financial_account_id=airtel_account_id() if source == "BUSINESS_ACCOUNT" else None,
            paid_to=data["paid_to"],
            interest_or_fees=money_value(data, "interest_or_fees"),
            reference=data["reference"],
            notes=notes,
        )
    operation = {
        "owner-funding": loans.record_owner_loan_to_business,
        "owner-drawing": loans.record_owner_drawing,
        "owner-repayment": loans.record_business_repayment_to_owner,
    }[action]
    kwargs = {"reference": data["reference"]} if action == "owner-drawing" else {}
    return operation(
        day,
        money_value(data, "amount"),
        financial_account_id=airtel_account_id(),
        notes=notes,
        **kwargs,
    )


@bp.route("/money/<action>", methods=["GET", "POST"])
@owner_required
def entry(action):
    if action not in ACTIONS:
        abort(404)
    fields = definition(action)
    token, error, status, preview = command_token(action), None, 200, None
    data = {item["name"]: request.form.get(item["name"], "") for item in fields}
    if request.method == "POST":
        try:
            if action == "salary" and request.form.get("intent") == "preview":
                year, month = salary_period(data)
                preview = payroll.get_salary_preview(
                    positive_id(data, "employment_id"),
                    year,
                    month,
                    money_value(data, "other_deductions"),
                )
            else:
                command(action, data, token, lambda: apply_operation(action, data))
                flash("Record saved.")
                return redirect(request.path, code=303)
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
        for item in fields:
            item["value"] = data[item["name"]]
    return render_template(
        "money_form.html",
        title=ACTIONS[action],
        active="more",
        fields=fields,
        command_token=token,
        error=error,
        reason=request.form.get("reason", ""),
        cancel_url="/driver-money"
        if action in {"salary", "advance", "reclassify-salary"}
        else "/loans"
        if action in {"loan", "repayment", "associate", "reclassify-loan"}
        else "/owner-money",
        salary_preview=preview,
        salary_form=action == "salary",
    ), status


@bp.route("/money/cancel/<kind>/<int:record_id>", methods=["GET", "POST"])
@owner_required
def cancel(kind, record_id):
    if kind not in CANCELLATIONS:
        abort(404)
    action = f"cancel-{kind}:{record_id}"
    token, error, status = command_token(action), None, 200
    if request.method == "POST":
        try:
            if request.form.get("confirm") != "on":
                raise ValueError("Confirm the reversal before continuing.")
            command(
                action,
                {"id": str(record_id), "confirm": "on"},
                token,
                lambda: CANCELLATIONS[kind](record_id, request.form.get("reason", "")),
            )
            flash("Record reversed.")
            return redirect(
                "/driver-money"
                if kind in {"advance", "salary"}
                else "/loans"
                if kind == "repayment"
                else "/owner-money",
                code=303,
            )
        except (ValueError, psycopg.IntegrityError, psycopg.DataError) as exc:
            error, status = safe_error(exc)
    return render_template(
        "confirm_delete.html",
        title="Reverse principal" if kind == "repayment" else "Reverse record",
        reversal=True,
        active="more",
        command_token=token,
        error=error,
    ), status


@bp.get("/driver-money", defaults={"employment_id": None})
@bp.get("/driver-money/<int:employment_id>")
@owner_required
def drivers(employment_id):
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        profiles = payroll.list_driver_money_profiles()
        try:
            detail = payroll.get_driver_money_detail(employment_id) if employment_id else None
        except ValueError:
            abort(404)
    return render_template(
        "driver_money.html", title="Driver Money", active="more", profiles=profiles, detail=detail
    )


@bp.get("/loans")
@owner_required
def loan_list():
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        rows, history = loans.list_business_loans(), loans.list_loan_repayments(100)
    return render_template(
        "loans.html", title="Loans", active="more", loans=rows, repayments=history
    )


@bp.get("/owner-money")
@owner_required
def owner():
    with shared_transaction(current_app.config["DB_SETTINGS"]) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        summary, activity = loans.get_owner_money_summary(), loans.list_owner_money_activity(100)
    return render_template(
        "owner_money.html", title="Owner Money", active="more", summary=summary, activity=activity
    )
