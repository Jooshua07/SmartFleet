import streamlit as st

from components.cards import empty_state
from services.bus_service import get_buses_overview
from services.cashing_service import (
    delete_cashing_collection,
    get_cashing_collection,
    get_collection_destination_account,
    get_recent_cashing_collections,
    update_direct_cashing_collection,
)
from services.smart_cashing_service import (
    build_standard_allocations,
    get_smart_cashing_preview,
    record_smart_cashing_collection,
)
from utils.cashing_form import (
    CASHING_FORM_VERSION_KEY,
    build_direct_cashing_entries,
    bus_option_label,
    clear_cashing_form_state,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


def _bus_options(buses: list[dict]) -> dict[str, dict]:
    return {bus_option_label(bus): bus for bus in buses}


def _registration_options(buses: list[dict]) -> dict[str, dict]:
    return {bus["registration_number"]: bus for bus in buses}


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


def _render_direct_collection_form(today, buses: list[dict], account: dict) -> None:
    form_version = int(st.session_state.setdefault(CASHING_FORM_VERSION_KEY, 0))
    key_prefix = f"cash_direct_{form_version}"
    bus_options = _bus_options(buses)

    with st.container(border=True):
        collection_date = st.date_input(
            "Collection date",
            value=today,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_date",
        )
        st.caption(
            f"Paid into {account['name']} ({account['account_type'].replace('_', ' ').title()})"
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
                financial_account_id=account["id"],
                entries=entries,
                notes=notes,
            )
            st.cache_data.clear()
            clear_cashing_form_state(st.session_state)
            st.session_state.cashing_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record cashing: {exc}", icon=":material/error:")


def _render_smart_collection_form(today, account: dict) -> None:
    form_version = int(st.session_state.setdefault(CASHING_FORM_VERSION_KEY, 0))
    key_prefix = f"cash_smart_{form_version}"

    backfill_mode = st.toggle("Backfill / edit date", key=f"{key_prefix}_backfill")
    if backfill_mode:
        collection_date = st.date_input(
            "Collection date",
            value=today,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_date",
        )
    else:
        collection_date = today
        st.caption(f"Collection date: {format_date(collection_date)}")

    st.caption(f"Paid into {account['name']} ({account['account_type'].replace('_', ' ').title()})")

    try:
        preview = get_smart_cashing_preview(collection_date)
    except Exception as exc:
        st.warning(str(exc), icon=":material/warning:")
        return

    buses = preview["buses"]
    if not buses:
        empty_state(
            "No eligible buses",
            "No bus was active during this collection coverage period.",
            ":material/directions_bus:",
        )
        return

    st.caption(
        f"Covers {format_date(preview['coverage_start'])} to {format_date(preview['coverage_end'])}"
    )
    bus_options = _registration_options(buses)
    selected_labels = st.multiselect(
        "Bus(es)",
        list(bus_options),
        default=list(bus_options),
        key=f"{key_prefix}_buses",
    )
    selected_buses = [bus_options[label] for label in selected_labels]
    selected_bus_ids = [bus["id"] for bus in selected_buses]

    sunday_labels = []
    if preview["collection_type"] == "THURSDAY":
        sunday_labels = st.pills(
            "Sunday workers",
            selected_labels,
            selection_mode="multi",
            key=f"{key_prefix}_sunday_workers",
        )
        st.caption(f"Sunday date: {format_date(preview['previous_sunday'])}")

    selected_sunday_ids = [
        bus_options[label]["id"]
        for label in sunday_labels
        if label in bus_options
    ]

    selected_expected = sum(
        (
            bus["expected_amount"]
            + (bus["sunday_rate"] if bus["id"] in selected_sunday_ids else 0)
            for bus in selected_buses
        ),
        0,
    )
    st.metric("Expected cashing", format_whole_kwacha(selected_expected), border=True)

    mode = st.segmented_control(
        "Recording mode",
        ["Standard", "Adjust Buses"],
        default="Standard",
        key=f"{key_prefix}_mode",
    )

    if mode == "Standard":
        with st.form(f"{key_prefix}_standard_form", border=False, clear_on_submit=True):
            total_received = st.number_input(
                "Actual received (K)",
                min_value=0.0,
                value=float(selected_expected),
                step=50.0,
            )
            shortage_classification = st.selectbox(
                "If short",
                ["UNKNOWN_DIFFERENCE", "UNDERPERFORMANCE"],
                index=0,
            )
            notes = st.text_area("Collection notes", height=70)
            submitted = st.form_submit_button("Save cashing", icon=":material/save:", type="primary")

        if submitted:
            try:
                allocation = build_standard_allocations(
                    preview,
                    selected_bus_ids,
                    selected_sunday_ids,
                    total_received,
                    shortage_classification,
                )
                record_smart_cashing_collection(
                    collection_date=collection_date,
                    financial_account_id=account["id"],
                    total_received=total_received,
                    entries=allocation["entries"],
                    unallocated_amount=allocation["unallocated_amount"],
                    difference_classification=allocation["difference_classification"],
                    cashing_mode="STANDARD",
                    notes=notes,
                )
                st.cache_data.clear()
                clear_cashing_form_state(st.session_state)
                st.session_state.cashing_saved = True
                st.rerun()
            except Exception as exc:
                st.error(f"Could not record cashing: {exc}", icon=":material/error:")
        return

    with st.form(f"{key_prefix}_adjust_form", border=False, clear_on_submit=True):
        total_received = st.number_input(
            "Actual received (K)",
            min_value=0.0,
            value=float(selected_expected),
            step=50.0,
        )
        adjusted_entries = []
        for bus in selected_buses:
            with st.container(border=True):
                st.markdown(f"**{bus['registration_number']}**")
                st.caption(bus["driver_name"] or "No assigned driver")
                normal_days = st.number_input(
                    "Normal days worked",
                    min_value=0,
                    max_value=3,
                    value=int(bus["normal_days"]),
                    step=1,
                    key=f"{key_prefix}_normal_days_{bus['id']}",
                )
                sunday_worked = False
                if preview["collection_type"] == "THURSDAY":
                    sunday_worked = st.checkbox(
                        "Worked previous Sunday",
                        value=bus["id"] in selected_sunday_ids,
                        key=f"{key_prefix}_sunday_{bus['id']}",
                    )
                expected = (
                    normal_days * bus["normal_daily_rate"]
                    + (bus["sunday_rate"] if sunday_worked else 0)
                )
                actual_amount = st.number_input(
                    "Bus allocation (K)",
                    min_value=0.0,
                    value=float(expected),
                    step=50.0,
                    key=f"{key_prefix}_actual_{bus['id']}",
                )
                classification = st.selectbox(
                    "Difference reason",
                    [
                        "MATCHED",
                        "REDUCED_WORKDAYS",
                        "UNDERPERFORMANCE",
                        "CONFIRMED_UNPAID_OBLIGATION",
                        "UNKNOWN_DIFFERENCE",
                        "SURPLUS",
                    ],
                    key=f"{key_prefix}_class_{bus['id']}",
                )
                responsible_type = st.selectbox(
                    "Responsible party type",
                    ["OTHER", "ASSIGNED_DRIVER", "HEAD_DRIVER"],
                    key=f"{key_prefix}_party_type_{bus['id']}",
                )
                responsible_name = st.text_input(
                    "Responsible party",
                    value=bus["driver_name"] or "",
                    key=f"{key_prefix}_party_name_{bus['id']}",
                )
                reason = st.text_input(
                    "Reason / note",
                    key=f"{key_prefix}_reason_{bus['id']}",
                )
                adjusted_entries.append(
                    {
                        "bus_id": bus["id"],
                        "normal_days": normal_days,
                        "normal_daily_rate": bus["normal_daily_rate"],
                        "sunday_days": 1 if sunday_worked else 0,
                        "sunday_rate": bus["sunday_rate"],
                        "actual_amount": actual_amount,
                        "allocation_provenance": "MANUAL_ADJUSTMENT",
                        "difference_classification": classification,
                        "worked_days_adjusted": normal_days != bus["normal_days"],
                        "sunday_worked": sunday_worked,
                        "explanation": reason,
                        "notes": reason,
                        "obligation": {
                            "responsible_party_type": responsible_type,
                            "responsible_party_name": responsible_name,
                            "amount": max(float(expected) - float(actual_amount), 0),
                            "notes": reason,
                        },
                    }
                )
        notes = st.text_area("Collection notes", height=70)
        submitted = st.form_submit_button("Save adjusted cashing", icon=":material/save:", type="primary")

    if submitted:
        try:
            allocation_total = sum(float(entry["actual_amount"]) for entry in adjusted_entries)
            unallocated_amount = float(total_received) - allocation_total
            if any(entry["difference_classification"] == "CONFIRMED_UNPAID_OBLIGATION" for entry in adjusted_entries):
                collection_classification = "CONFIRMED_UNPAID_OBLIGATION"
            elif unallocated_amount > 0:
                collection_classification = "SURPLUS"
            elif unallocated_amount < 0:
                collection_classification = "UNKNOWN_DIFFERENCE"
            else:
                collection_classification = "MATCHED"
            record_smart_cashing_collection(
                collection_date=collection_date,
                financial_account_id=account["id"],
                total_received=total_received,
                entries=adjusted_entries,
                unallocated_amount=unallocated_amount,
                difference_classification=collection_classification,
                cashing_mode="ADJUSTED",
                notes=notes,
            )
            st.cache_data.clear()
            clear_cashing_form_state(st.session_state)
            st.session_state.cashing_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record cashing: {exc}", icon=":material/error:")


def _render_edit_collection(collection_id: int, account: dict) -> None:
    details = get_cashing_collection(collection_id)
    collection = details["collection"]
    entries = details["entries"]

    st.subheader("Edit cashing")
    with st.form(f"edit_cashing_form_{collection_id}"):
        collection_date = st.date_input(
            "Collection date",
            value=collection["collection_date"],
            format="DD/MM/YYYY",
            key=f"edit_cashing_date_{collection_id}",
        )
        st.caption(
            f"Paid into {account['name']} ({account['account_type'].replace('_', ' ').title()})"
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
                financial_account_id=account["id"],
                entries=updated_entries,
                notes=notes,
            )
            st.cache_data.clear()
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
try:
    collection_account = get_collection_destination_account()
except Exception as exc:
    collection_account = None
    account_error = str(exc)

if collection_account is None:
    empty_state(
        "No Airtel Money account",
        account_error,
        ":material/account_balance:",
    )
else:
    if st.session_state.pop("cashing_saved", False):
        st.success("Cashing recorded.", icon=":material/check_circle:")

    edit_id = st.session_state.get("edit_cashing_id")
    if edit_id:
        try:
            _render_edit_collection(edit_id, collection_account)
        except Exception as exc:
            st.error(f"Could not load cashing: {exc}", icon=":material/error:")
    else:
        _render_smart_collection_form(today, collection_account)

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
                            st.cache_data.clear()
                            st.session_state.pop("delete_cashing_id", None)
                            st.success("Cashing deleted.", icon=":material/check_circle:")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not delete cashing: {exc}", icon=":material/error:")
                    if st.button("Cancel", key=f"cancel_delete_cashing_{collection['id']}"):
                        st.session_state.pop("delete_cashing_id", None)
                        st.rerun()
