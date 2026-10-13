import importlib

import streamlit as st

from components.cards import empty_state
from services.bus_service import get_buses_overview
import services.expense_service as expense_service
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


if not hasattr(expense_service, "get_operating_expense_categories"):
    expense_service = importlib.reload(expense_service)
delete_business_expense = expense_service.delete_business_expense
get_expense = expense_service.get_expense
get_operating_expense_categories = expense_service.get_operating_expense_categories
get_recent_expenses = expense_service.get_recent_expenses
record_business_expense = expense_service.record_business_expense
update_business_expense = expense_service.update_business_expense


def _option_map(rows: list[dict], label_key: str = "name") -> dict[str, int]:
    return {row[label_key]: row["id"] for row in rows}


def _category_group(name: str) -> str:
    if name in {"Maintenance", "Parts"}:
        return "Bus"
    if name in {"Driver Salaries", "Driver Advances"}:
        return "Driver"
    if name in {"Transfer Fees", "Loan Repayments", "Owner Drawings"}:
        return "Finance"
    if name == "Office & Administration":
        return "Admin"
    return "Other"


def _category_options(categories: list[dict]) -> dict[str, int]:
    return {f"{_category_group(row['name'])} - {row['name']}": row["id"] for row in categories}


def _render_expense_form(
    categories: list[dict],
    buses: list[dict],
    today,
    expense: dict | None = None,
) -> None:
    is_edit = expense is not None
    form_key = f"expense_form_{expense['id']}" if is_edit else "record_expense_form"
    category_options = _category_options(categories)
    category_labels = list(category_options)

    selected_category_index = 0
    if is_edit:
        selected_category_index = next(
            (
                index
                for index, label in enumerate(category_labels)
                if category_options[label] == expense["category_id"]
            ),
            0,
        )

    scope_options = ["General Business"]
    if buses:
        scope_options.append("Specific Bus")
    default_scope = "Specific Bus" if is_edit and expense["scope"] == "BUS" and buses else "General Business"

    scope_label = st.segmented_control(
        "Expense scope",
        scope_options,
        default=default_scope,
        key=f"expense_scope_{form_key}",
    )

    with st.form(form_key):
        expense_date = st.date_input(
            "Expense date",
            value=expense["expense_date"] if is_edit else today,
            format="DD/MM/YYYY",
            key=f"expense_date_{form_key}",
        )
        selected_category = st.selectbox(
            "Category",
            category_labels,
            index=selected_category_index,
            key=f"expense_category_{form_key}",
        )

        bus_id = None
        if scope_label == "Specific Bus":
            bus_options = {
                f"{bus['registration_number']} | {bus['driver_name'] or 'No driver'}": bus["id"]
                for bus in buses
            }
            bus_labels = list(bus_options)
            selected_bus_index = 0
            if is_edit:
                selected_bus_index = next(
                    (
                        index
                        for index, label in enumerate(bus_labels)
                        if bus_options[label] == expense["bus_id"]
                    ),
                    0,
                )
            selected_bus = st.selectbox(
                "Bus",
                bus_labels,
                index=selected_bus_index,
                key=f"expense_bus_{form_key}",
            )
            bus_id = bus_options[selected_bus]

        amount = st.number_input(
            "Amount (K)",
            min_value=0.0,
            value=float(expense["amount"]) if is_edit else 0.0,
            step=50.0,
            key=f"expense_amount_{form_key}",
        )
        description = st.text_input(
            "Expense title",
            value=expense["description"] if is_edit else "",
            placeholder="e.g. AIH tyres",
            key=f"expense_description_{form_key}",
        )
        st.caption("Use at most five words and 35 characters. Put longer details in Notes.")
        vendor_name = st.text_input(
            "Paid to",
            value=expense["vendor_name"] or "" if is_edit else "",
            placeholder="Person, shop or supplier",
            key=f"expense_vendor_{form_key}",
        )
        reference_number = st.text_input(
            "Receipt/reference",
            value=expense["reference_number"] or "" if is_edit else "",
            placeholder="Receipt number, note number or mobile money ref",
            key=f"expense_reference_{form_key}",
        )
        notes = st.text_area(
            "Notes",
            value=expense["notes"] or "" if is_edit else "",
            height=80,
            key=f"expense_notes_{form_key}",
        )
        submitted = st.form_submit_button(
            "Update expense" if is_edit else "Save expense",
            icon=":material/save:",
            type="primary",
        )

    if submitted:
        try:
            payload = {
                "expense_date": expense_date,
                "category_id": category_options[selected_category],
                "amount": amount,
                "description": description,
                "scope": "BUS" if scope_label == "Specific Bus" else "GENERAL",
                "bus_id": bus_id,
                "vendor_name": vendor_name,
                "reference_number": reference_number,
                "notes": notes,
            }
            if is_edit:
                update_business_expense(expense_id=expense["id"], **payload)
                st.session_state.pop("edit_expense_id", None)
            else:
                record_business_expense(**payload)
            st.cache_data.clear()
            st.session_state.expense_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save expense: {exc}", icon=":material/error:")


st.subheader("Record Expense")

today = today_lusaka()
categories = get_operating_expense_categories()
buses = get_buses_overview(today)

if st.session_state.pop("expense_saved", False):
    st.success("Expense recorded.", icon=":material/check_circle:")

if not categories:
    empty_state(
        "No expense categories",
        "Add active expense categories before recording expenses.",
        ":material/category:",
    )
else:
    edit_id = st.session_state.get("edit_expense_id")
    if edit_id:
        try:
            st.subheader("Edit expense")
            _render_expense_form(categories, buses, today, expense=get_expense(edit_id))
            if st.button("Cancel edit", icon=":material/close:"):
                st.session_state.pop("edit_expense_id", None)
                st.rerun()
        except Exception as exc:
            st.error(f"Could not load expense: {exc}", icon=":material/error:")
    else:
        _render_expense_form(categories, buses, today)

recent = get_recent_expenses(limit=10)
if recent:
    st.subheader("Recent expenses")
    for expense in recent:
        with st.container(border=True):
            st.markdown(f"**{expense['description']}**")
            if expense["vendor_name"]:
                st.caption(f"Paid to: {expense['vendor_name']}")
            if expense["reference_number"]:
                st.caption(f"Reference: {expense['reference_number']}")
            if expense["registration_number"]:
                st.caption(
                    f"{format_date(expense['expense_date'])} | Specific Bus | {expense['category_name']} | "
                    f"{expense['registration_number']}"
                )
            else:
                st.caption(f"{format_date(expense['expense_date'])} | General Business | {expense['category_name']}")
            st.markdown(format_whole_kwacha(expense["amount"]))
            with st.container(horizontal=True):
                if st.button("Edit", icon=":material/edit:", key=f"edit_expense_{expense['id']}"):
                    st.session_state.edit_expense_id = expense["id"]
                    st.rerun()
                if st.button("Delete", icon=":material/delete:", key=f"delete_expense_{expense['id']}"):
                    st.session_state.delete_expense_id = expense["id"]
                    st.rerun()

            if st.session_state.get("delete_expense_id") == expense["id"]:
                st.warning("Delete this expense and its matching ledger entry?", icon=":material/warning:")
                with st.container(horizontal=True):
                    if st.button(
                        "Confirm delete",
                        icon=":material/delete_forever:",
                        type="primary",
                        key=f"confirm_delete_expense_{expense['id']}",
                    ):
                        try:
                            delete_business_expense(expense["id"])
                            st.cache_data.clear()
                            st.session_state.pop("delete_expense_id", None)
                            st.success("Expense deleted.", icon=":material/check_circle:")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not delete expense: {exc}", icon=":material/error:")
                    if st.button("Cancel", key=f"cancel_delete_expense_{expense['id']}"):
                        st.session_state.pop("delete_expense_id", None)
                        st.rerun()
