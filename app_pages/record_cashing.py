import streamlit as st

from components.cards import empty_state
from services.cashing_service import (
    delete_cashing_collection,
    get_cashing_collection,
    get_collection_destination_account,
    get_recent_cashing_collections,
    update_direct_cashing_collection,
)
from services.smart_cashing_service import (
    build_standard_allocations,
    get_cashing_obligations_for_collection,
    get_smart_cashing_preview,
    list_cashing_obligation_payments,
    list_open_cashing_obligations,
    record_obligation_payment,
    record_smart_cashing_collection,
    update_smart_cashing_collection,
)
from utils.cashing_form import (
    CASHING_FORM_VERSION_KEY,
    clear_cashing_form_state,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


def _classification_label(value: str | None) -> str:
    return (value or "MATCHED").replace("_", " ").title()


def _mode_label(value: str | None) -> str:
    if value == "STANDARD":
        return "Standard"
    if value == "ADJUSTED":
        return "Adjusted"
    return "Direct"


def _collection_classification(entries: list[dict], unallocated_amount: float) -> str:
    if any(entry["difference_classification"] == "CONFIRMED_UNPAID_OBLIGATION" for entry in entries):
        return "CONFIRMED_UNPAID_OBLIGATION"
    if unallocated_amount > 0:
        return "SURPLUS"
    if unallocated_amount < 0:
        return "UNKNOWN_DIFFERENCE"
    for entry in entries:
        if entry["difference_classification"] != "MATCHED":
            return entry["difference_classification"]
    return "MATCHED"


def _registration_options(buses: list[dict]) -> dict[str, dict]:
    return {bus["registration_number"]: bus for bus in buses}




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
            collection_classification = _collection_classification(adjusted_entries, unallocated_amount)
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


def _render_smart_collection_detail(collection_id: int) -> None:
    details = get_cashing_collection(collection_id)
    collection = details["collection"]
    entries = details["entries"]
    obligations = get_cashing_obligations_for_collection(collection_id)

    st.subheader("Cashing details")
    with st.container(border=True):
        st.markdown(f"**{format_date(collection['collection_date'])}**")
        st.caption(
            f"{_mode_label(collection['cashing_mode'])} | "
            f"{_classification_label(collection['difference_classification'])}"
        )
        if collection["coverage_start"] and collection["coverage_end"]:
            st.caption(
                f"Covers {format_date(collection['coverage_start'])} to "
                f"{format_date(collection['coverage_end'])}"
            )
        with st.container(horizontal=True):
            st.metric("Received", format_whole_kwacha(collection["total_amount"]), border=True)
            st.metric("Expected", format_whole_kwacha(collection["expected_total"]), border=True)
            st.metric("Difference", format_whole_kwacha(collection["unallocated_amount"]), border=True)
        if collection["notes"]:
            st.caption(collection["notes"])

    st.markdown("**Bus allocations**")
    for entry in entries:
        with st.container(border=True):
            st.markdown(f"**{entry['registration_number']}**")
            st.caption(
                f"{entry['normal_days']} normal day(s), {entry['sunday_days']} Sunday | "
                f"{_classification_label(entry['difference_classification'])}"
            )
            with st.container(horizontal=True):
                st.metric("Allocated", format_whole_kwacha(entry["actual_amount"]), border=True)
                st.metric("Expected", format_whole_kwacha(entry["expected_amount"]), border=True)
                st.metric("Variance", format_whole_kwacha(entry["variance"]), border=True)
            if entry["explanation"]:
                st.caption(entry["explanation"])

    if obligations:
        st.markdown("**Obligations on this cashing**")
        for obligation in obligations:
            with st.container(border=True):
                st.markdown(
                    f"**{obligation['registration_number']} | "
                    f"{obligation['responsible_party_name']}**"
                )
                st.caption(
                    f"{obligation['responsible_party_type'].replace('_', ' ').title()} | "
                    f"{obligation['status'].replace('_', ' ').title()}"
                )
                with st.container(horizontal=True):
                    st.metric("Original", format_whole_kwacha(obligation["amount"]), border=True)
                    st.metric("Paid", format_whole_kwacha(obligation["paid_amount"]), border=True)
                    st.metric("Outstanding", format_whole_kwacha(obligation["outstanding_amount"]), border=True)
                if obligation["notes"]:
                    st.caption(obligation["notes"])
                payments = list_cashing_obligation_payments(obligation["id"])
                if payments:
                    st.caption("Payment history")
                    for payment in payments:
                        st.caption(
                            f"{format_date(payment['payment_date'])} | "
                            f"{format_whole_kwacha(payment['amount'])} | {payment['account_name']}"
                        )

    if st.button("Close details", icon=":material/close:", key=f"close_cashing_detail_{collection_id}"):
        st.session_state.pop("detail_cashing_id", None)
        st.rerun()


def _render_smart_correction_form(collection_id: int, account: dict) -> None:
    details = get_cashing_collection(collection_id)
    collection = details["collection"]
    entries = details["entries"]
    obligations = get_cashing_obligations_for_collection(collection_id)

    st.subheader("Correct smart cashing")
    if collection["cashing_mode"] == "DIRECT":
        st.warning("Use Edit for older direct cashing records.", icon=":material/warning:")
        if st.button("Close correction", icon=":material/close:", key=f"close_smart_correction_{collection_id}"):
            st.session_state.pop("correct_cashing_id", None)
            st.rerun()
        return

    locked = any(
        obligation["status"] != "VOID" or obligation["paid_amount"] > 0
        for obligation in obligations
    )
    if locked:
        st.warning(
            "This cashing has obligations or payments. Use the obligation/payment records instead of editing it.",
            icon=":material/lock:",
        )
        if st.button("Close correction", icon=":material/close:", key=f"close_locked_correction_{collection_id}"):
            st.session_state.pop("correct_cashing_id", None)
            st.rerun()
        return

    with st.form(f"correct_smart_cashing_{collection_id}", border=False):
        collection_date = st.date_input(
            "Collection date",
            value=collection["collection_date"],
            format="DD/MM/YYYY",
            key=f"correct_smart_date_{collection_id}",
        )
        st.caption(
            f"Paid into {account['name']} ({account['account_type'].replace('_', ' ').title()})"
        )
        total_received = st.number_input(
            "Actual received (K)",
            min_value=0.0,
            value=float(collection["total_amount"]),
            step=50.0,
            key=f"correct_smart_total_{collection_id}",
        )
        corrected_entries = []
        for entry in entries:
            with st.container(border=True):
                st.markdown(f"**{entry['registration_number']}**")
                normal_days = st.number_input(
                    "Normal days worked",
                    min_value=0,
                    max_value=7,
                    value=int(entry["normal_days"]),
                    step=1,
                    key=f"correct_smart_normal_{entry['id']}",
                )
                sunday_days = st.number_input(
                    "Sunday days",
                    min_value=0,
                    max_value=1,
                    value=int(entry["sunday_days"]),
                    step=1,
                    key=f"correct_smart_sunday_{entry['id']}",
                )
                actual_amount = st.number_input(
                    "Bus allocation (K)",
                    min_value=0.0,
                    value=float(entry["actual_amount"]),
                    step=50.0,
                    key=f"correct_smart_amount_{entry['id']}",
                )
                classification_options = [
                    "MATCHED",
                    "REDUCED_WORKDAYS",
                    "UNDERPERFORMANCE",
                    "CONFIRMED_UNPAID_OBLIGATION",
                    "UNKNOWN_DIFFERENCE",
                    "SURPLUS",
                ]
                classification = st.selectbox(
                    "Difference reason",
                    classification_options,
                    index=classification_options.index(entry["difference_classification"]),
                    key=f"correct_smart_class_{entry['id']}",
                )
                responsible_type = st.selectbox(
                    "Responsible party type",
                    ["OTHER", "ASSIGNED_DRIVER", "HEAD_DRIVER"],
                    key=f"correct_smart_party_type_{entry['id']}",
                )
                responsible_name = st.text_input(
                    "Responsible party",
                    key=f"correct_smart_party_name_{entry['id']}",
                )
                reason = st.text_input(
                    "Reason / note",
                    value=entry["explanation"] or "",
                    key=f"correct_smart_reason_{entry['id']}",
                )
                expected_amount = (
                    normal_days * float(entry["normal_daily_rate"])
                    + sunday_days * float(entry["sunday_rate"])
                )
                obligation_amount = max(expected_amount - float(actual_amount), 0)
                corrected_entries.append(
                    {
                        "bus_id": entry["bus_id"],
                        "normal_days": normal_days,
                        "normal_daily_rate": entry["normal_daily_rate"],
                        "sunday_days": sunday_days,
                        "sunday_rate": entry["sunday_rate"],
                        "actual_amount": actual_amount,
                        "allocation_provenance": "MANUAL_ADJUSTMENT",
                        "difference_classification": classification,
                        "worked_days_adjusted": normal_days != entry["normal_days"],
                        "sunday_worked": sunday_days > 0,
                        "explanation": reason,
                        "notes": reason,
                        "obligation": {
                            "responsible_party_type": responsible_type,
                            "responsible_party_name": responsible_name,
                            "amount": obligation_amount,
                            "notes": reason,
                        },
                    }
                )

        correction_reason = st.text_area(
            "Correction note",
            value=collection["notes"] or "",
            height=80,
            key=f"correct_smart_notes_{collection_id}",
        )
        submitted = st.form_submit_button(
            "Save correction",
            icon=":material/save:",
            type="primary",
        )

    if submitted:
        try:
            allocation_total = sum(float(entry["actual_amount"]) for entry in corrected_entries)
            unallocated_amount = float(total_received) - allocation_total
            update_smart_cashing_collection(
                collection_id=collection_id,
                collection_date=collection_date,
                financial_account_id=account["id"],
                total_received=total_received,
                entries=corrected_entries,
                unallocated_amount=unallocated_amount,
                difference_classification=_collection_classification(corrected_entries, unallocated_amount),
                cashing_mode="ADJUSTED",
                notes=correction_reason,
            )
            st.cache_data.clear()
            st.session_state.pop("correct_cashing_id", None)
            st.session_state.cashing_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save correction: {exc}", icon=":material/error:")

    if st.button("Cancel correction", icon=":material/close:", key=f"cancel_smart_correction_{collection_id}"):
        st.session_state.pop("correct_cashing_id", None)
        st.rerun()


def _render_obligation_payment_form(obligation: dict, account: dict, today) -> None:
    form_key = f"obligation_payment_{obligation['id']}"
    with st.form(form_key, border=False, clear_on_submit=True):
        payment_date = st.date_input(
            "Payment date",
            value=today,
            format="DD/MM/YYYY",
            key=f"{form_key}_date",
        )
        amount = st.number_input(
            "Amount received (K)",
            min_value=0.0,
            max_value=float(obligation["outstanding_amount"]),
            value=float(obligation["outstanding_amount"]),
            step=50.0,
            key=f"{form_key}_amount",
        )
        notes = st.text_area(
            "Payment notes",
            height=70,
            key=f"{form_key}_notes",
        )
        submitted = st.form_submit_button(
            "Save payment",
            icon=":material/save:",
            type="primary",
        )

    if submitted:
        try:
            record_obligation_payment(
                obligation_id=obligation["id"],
                payment_date=payment_date,
                amount=amount,
                financial_account_id=account["id"],
                notes=notes,
            )
            st.cache_data.clear()
            st.session_state.pop("pay_obligation_id", None)
            st.session_state.obligation_payment_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record obligation payment: {exc}", icon=":material/error:")


def _render_open_obligations(account: dict, today) -> None:
    obligations = list_open_cashing_obligations(limit=12)
    if not obligations:
        return

    st.subheader("Open cashing obligations")
    for obligation in obligations:
        with st.container(border=True):
            st.markdown(
                f"**{obligation['registration_number']} | "
                f"{obligation['responsible_party_name']}**"
            )
            st.caption(
                f"Cashing: {format_date(obligation['collection_date'])} | "
                f"Recognized: {format_date(obligation['recognized_date'])} | "
                f"{obligation['responsible_party_type'].replace('_', ' ').title()}"
            )
            with st.container(horizontal=True):
                st.metric("Original", format_whole_kwacha(obligation["amount"]), border=True)
                st.metric("Paid", format_whole_kwacha(obligation["paid_amount"]), border=True)
                st.metric("Outstanding", format_whole_kwacha(obligation["outstanding_amount"]), border=True)
            if obligation["notes"]:
                st.caption(obligation["notes"])

            if st.button(
                "Record payment",
                icon=":material/payments:",
                key=f"pay_obligation_{obligation['id']}",
            ):
                st.session_state.pay_obligation_id = obligation["id"]
                st.rerun()

            if st.session_state.get("pay_obligation_id") == obligation["id"]:
                st.caption(
                    f"Paid into {account['name']} "
                    f"({account['account_type'].replace('_', ' ').title()})"
                )
                _render_obligation_payment_form(obligation, account, today)


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
    if st.session_state.pop("obligation_payment_saved", False):
        st.success("Obligation payment recorded.", icon=":material/check_circle:")

    edit_id = st.session_state.get("edit_cashing_id")
    detail_id = st.session_state.get("detail_cashing_id")
    correct_id = st.session_state.get("correct_cashing_id")
    if edit_id:
        try:
            _render_edit_collection(edit_id, collection_account)
        except Exception as exc:
            st.error(f"Could not load cashing: {exc}", icon=":material/error:")
    elif correct_id:
        try:
            _render_smart_correction_form(correct_id, collection_account)
        except Exception as exc:
            st.error(f"Could not load smart correction: {exc}", icon=":material/error:")
    elif detail_id:
        try:
            _render_smart_collection_detail(detail_id)
        except Exception as exc:
            st.error(f"Could not load cashing details: {exc}", icon=":material/error:")
    else:
        _render_smart_collection_form(today, collection_account)

recent = get_recent_cashing_collections(limit=14)
if recent:
    st.subheader("Recent cashing")
    for collection in recent:
        with st.container(border=True):
            st.markdown(f"**{format_date(collection['collection_date'])}**")
            st.caption(
                f"{_mode_label(collection['cashing_mode'])} | "
                f"{collection['bus_count']} bus entries | {collection['account_name']}"
            )
            if collection["coverage_start"] and collection["coverage_end"]:
                st.caption(
                    f"Covers {format_date(collection['coverage_start'])} to "
                    f"{format_date(collection['coverage_end'])}"
                )
            with st.container(horizontal=True):
                st.metric("Received", format_whole_kwacha(collection["total_amount"]), border=True)
                st.metric("Expected", format_whole_kwacha(collection["expected_total"]), border=True)
                st.metric("Difference", format_whole_kwacha(collection["unallocated_amount"]), border=True)
            if collection["difference_classification"] != "MATCHED":
                st.caption(_classification_label(collection["difference_classification"]))
            if collection["outstanding_amount"] and collection["outstanding_amount"] > 0:
                st.warning(
                    f"Outstanding obligation: {format_whole_kwacha(collection['outstanding_amount'])}",
                    icon=":material/warning:",
                )
            with st.container(horizontal=True):
                if collection["cashing_mode"] == "DIRECT":
                    if st.button("Edit", icon=":material/edit:", key=f"edit_cashing_{collection['id']}"):
                        st.session_state.edit_cashing_id = collection["id"]
                        st.rerun()
                    delete_disabled = False
                else:
                    if st.button("Details", icon=":material/receipt_long:", key=f"detail_cashing_{collection['id']}"):
                        st.session_state.detail_cashing_id = collection["id"]
                        st.rerun()
                    locked_by_obligations = bool(collection["obligation_count"])
                    if st.button(
                        "Correct",
                        icon=":material/edit_note:",
                        key=f"correct_cashing_{collection['id']}",
                        disabled=locked_by_obligations,
                    ):
                        st.session_state.correct_cashing_id = collection["id"]
                        st.rerun()
                    if locked_by_obligations:
                        st.caption("Correction locked by obligations or payments.")
                    delete_disabled = locked_by_obligations
                if st.button(
                    "Delete",
                    icon=":material/delete:",
                    key=f"delete_cashing_{collection['id']}",
                    disabled=delete_disabled,
                ):
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

if collection_account is not None:
    _render_open_obligations(collection_account, today)
