import streamlit as st

from components.cards import empty_state
from services.bus_service import get_buses_overview
from services.cashing_service import (
    delete_cashing_collection,
    get_active_financial_accounts,
    get_cashing_collection,
    get_recent_cashing_collections,
    record_direct_cashing_collection,
    update_direct_cashing_collection,
)
from utils.cashing_form import (
    CASHING_FORM_VERSION_KEY,
    build_direct_cashing_entries,
    bus_option_label,
    clear_cashing_form_state,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


def _account_options(accounts: list[dict]) -> dict[str, int]:
    return {
        f"{account['name']} ({account['account_type']})": account["id"]
        for account in accounts
    }


def _bus_options(buses: list[dict]) -> dict[str, dict]:
    return {bus_option_label(bus): bus for bus in buses}


def _render_amount_fields(
    selected_buses: list[dict],
    key_prefix: str,
    add_sunday: bool,
    different_amounts: bool,
) -> tuple[dict[int, float], dict[int, float], dict[int, str]]:
    normal_amounts = {}
    sunday_amounts = {}
    reasons = {}
    multiple_buses = len(selected_buses) > 1

    if multiple_buses and not different_amounts:
        amount = st.number_input(
            "Amount per selected bus (K)",
            min_value=0.0,
            value=0.0,
            step=50.0,
            key=f"{key_prefix}_common_amount",
        )
        sunday_amount = 0.0
        if add_sunday:
            sunday_amount = st.number_input(
                "Sunday amount per selected bus (K)",
                min_value=0.0,
                value=0.0,
                step=50.0,
                key=f"{key_prefix}_common_sunday",
            )
        reason = st.text_input(
            "Reason if different",
            placeholder="Optional note for this cashing",
            key=f"{key_prefix}_common_reason",
        )

        for bus in selected_buses:
            normal_amounts[bus["id"]] = amount
            sunday_amounts[bus["id"]] = sunday_amount
            reasons[bus["id"]] = reason
        return normal_amounts, sunday_amounts, reasons

    for bus in selected_buses:
        with st.container(border=True):
            st.markdown(f"**{bus['registration_number']}**")
            st.caption(f"{bus['driver_name'] or 'No assigned driver'} | {bus['route_name']}")
            normal_amounts[bus["id"]] = st.number_input(
                "Amount (K)",
                min_value=0.0,
                value=0.0,
                step=50.0,
                key=f"{key_prefix}_amount_{bus['id']}",
            )
            sunday_amounts[bus["id"]] = 0.0
            if add_sunday:
                sunday_amounts[bus["id"]] = st.number_input(
                    "Sunday amount (K)",
                    min_value=0.0,
                    value=0.0,
                    step=50.0,
                    key=f"{key_prefix}_sunday_{bus['id']}",
                )
            reasons[bus["id"]] = st.text_input(
                "Reason if different",
                placeholder="Optional note for this bus",
                key=f"{key_prefix}_reason_{bus['id']}",
            )

    return normal_amounts, sunday_amounts, reasons


def _render_direct_collection_form(today, buses: list[dict], accounts: list[dict]) -> None:
    form_version = int(st.session_state.setdefault(CASHING_FORM_VERSION_KEY, 0))
    key_prefix = f"cash_direct_{form_version}"
    account_options = _account_options(accounts)
    bus_options = _bus_options(buses)

    with st.container(border=True):
        collection_date = st.date_input(
            "Collection date",
            value=today,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_date",
        )
        selected_account = st.selectbox(
            "Paid into",
            list(account_options),
            index=0,
            key=f"{key_prefix}_account",
        )
        selected_labels = st.multiselect(
            "Bus(es)",
            list(bus_options),
            placeholder="Choose one or more buses",
            key=f"{key_prefix}_buses",
        )
        selected_buses = [bus_options[label] for label in selected_labels]

        if not selected_buses:
            st.info("Choose one or more buses to enter cashing.", icon=":material/directions_bus:")
            return

        add_sunday = st.toggle("Add Sunday", key=f"{key_prefix}_add_sunday")
        different_amounts = False
        if len(selected_buses) > 1:
            different_amounts = st.toggle(
                "Different amounts per bus",
                key=f"{key_prefix}_different_amounts",
            )

        with st.form(f"{key_prefix}_form", border=False, clear_on_submit=True):
            normal_amounts, sunday_amounts, reasons = _render_amount_fields(
                selected_buses,
                key_prefix,
                add_sunday,
                different_amounts,
            )
            notes = st.text_area(
                "Collection notes",
                height=70,
                key=f"{key_prefix}_notes",
            )
            total_preview = sum(normal_amounts.values()) + sum(sunday_amounts.values())
            st.metric("Total to save", format_whole_kwacha(total_preview), border=True)
            submitted = st.form_submit_button(
                "Save cashing",
                icon=":material/save:",
                type="primary",
            )

    if submitted:
        try:
            entries = build_direct_cashing_entries(
                selected_bus_ids=[bus["id"] for bus in selected_buses],
                normal_amounts=normal_amounts,
                sunday_amounts=sunday_amounts,
                reasons=reasons,
            )
            record_direct_cashing_collection(
                collection_date=collection_date,
                financial_account_id=account_options[selected_account],
                entries=entries,
                notes=notes,
            )
            clear_cashing_form_state(st.session_state)
            st.session_state.cashing_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record cashing: {exc}", icon=":material/error:")


def _render_edit_collection(collection_id: int, accounts: list[dict]) -> None:
    details = get_cashing_collection(collection_id)
    collection = details["collection"]
    entries = details["entries"]
    account_options = _account_options(accounts)
    account_labels = list(account_options)
    selected_account_index = next(
        (
            index
            for index, label in enumerate(account_labels)
            if account_options[label] == collection["financial_account_id"]
        ),
        0,
    )

    st.subheader("Edit cashing")
    with st.form(f"edit_cashing_form_{collection_id}"):
        collection_date = st.date_input(
            "Collection date",
            value=collection["collection_date"],
            format="DD/MM/YYYY",
            key=f"edit_cashing_date_{collection_id}",
        )
        selected_account = st.selectbox(
            "Paid into",
            account_labels,
            index=selected_account_index,
            key=f"edit_cashing_account_{collection_id}",
        )
        notes = st.text_area(
            "Collection notes",
            value=collection["notes"] or "",
            height=80,
            key=f"edit_cashing_notes_{collection_id}",
        )

        updated_entries = []
        for entry in entries:
            with st.container(border=True):
                keep_entry = st.checkbox(
                    entry["registration_number"],
                    value=True,
                    key=f"edit_cash_keep_{entry['id']}",
                )
                amount = st.number_input(
                    "Amount (K)",
                    min_value=0.0,
                    value=float(entry["actual_amount"]),
                    step=50.0,
                    key=f"edit_cash_amount_{entry['id']}",
                )
                reason = st.text_input(
                    "Reason if different",
                    value=entry["explanation"] or "",
                    key=f"edit_cash_reason_{entry['id']}",
                )
                bus_notes = st.text_input(
                    "Bus notes",
                    value=entry["notes"] or "",
                    key=f"edit_cash_notes_{entry['id']}",
                )
                updated_entries.append(
                    {
                        "include": keep_entry,
                        "bus_id": entry["bus_id"],
                        "normal_amount": amount,
                        "sunday_amount": 0,
                        "explanation": reason,
                        "notes": bus_notes,
                    }
                )

        submitted = st.form_submit_button("Update cashing", icon=":material/save:", type="primary")

    if submitted:
        try:
            update_direct_cashing_collection(
                collection_id=collection_id,
                collection_date=collection_date,
                financial_account_id=account_options[selected_account],
                entries=updated_entries,
                notes=notes,
            )
            st.session_state.pop("edit_cashing_id", None)
            st.session_state.cashing_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not update cashing: {exc}", icon=":material/error:")

    if st.button("Cancel edit", icon=":material/close:", key=f"cancel_edit_cashing_{collection_id}"):
        st.session_state.pop("edit_cashing_id", None)
        st.rerun()


st.subheader("Record Cashing")

today = today_lusaka()
buses = get_buses_overview(today, status="ACTIVE")
accounts = get_active_financial_accounts()

if not buses:
    empty_state(
        "No active buses",
        "Register an active bus before recording cashing.",
        ":material/directions_bus:",
    )
elif not accounts:
    empty_state(
        "No active accounts",
        "Add an active cash, Airtel Money or bank account before recording cashing.",
        ":material/account_balance:",
    )
else:
    if st.session_state.pop("cashing_saved", False):
        st.success("Cashing recorded.", icon=":material/check_circle:")

    edit_id = st.session_state.get("edit_cashing_id")
    if edit_id:
        try:
            _render_edit_collection(edit_id, accounts)
        except Exception as exc:
            st.error(f"Could not load cashing: {exc}", icon=":material/error:")
    else:
        _render_direct_collection_form(today, buses, accounts)

recent = get_recent_cashing_collections(limit=14)
if recent:
    st.subheader("Recent cashing")
    for collection in recent:
        with st.container(border=True):
            st.markdown(f"**{format_date(collection['collection_date'])}**")
            st.caption(f"{collection['bus_count']} bus entries | {collection['account_name']}")
            st.markdown(format_whole_kwacha(collection["total_amount"]))
            with st.container(horizontal=True):
                if st.button("Edit", icon=":material/edit:", key=f"edit_cashing_{collection['id']}"):
                    st.session_state.edit_cashing_id = collection["id"]
                    st.rerun()
                if st.button("Delete", icon=":material/delete:", key=f"delete_cashing_{collection['id']}"):
                    st.session_state.delete_cashing_id = collection["id"]
                    st.rerun()

            if st.session_state.get("delete_cashing_id") == collection["id"]:
                st.warning("Delete this cashing collection and its ledger entry?", icon=":material/warning:")
                with st.container(horizontal=True):
                    if st.button(
                        "Confirm delete",
                        icon=":material/delete_forever:",
                        type="primary",
                        key=f"confirm_delete_cashing_{collection['id']}",
                    ):
                        try:
                            delete_cashing_collection(collection["id"])
                            st.session_state.pop("delete_cashing_id", None)
                            st.success("Cashing deleted.", icon=":material/check_circle:")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not delete cashing: {exc}", icon=":material/error:")
                    if st.button("Cancel", key=f"cancel_delete_cashing_{collection['id']}"):
                        st.session_state.pop("delete_cashing_id", None)
                        st.rerun()
