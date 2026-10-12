from datetime import date, timedelta

import streamlit as st

from components.cards import empty_state
from services.driver_service import get_drivers_overview
from services.preset_service import (
    get_business_settings,
    list_cashing_rates,
    list_cashing_schedule_rules,
    list_driver_salary_presets,
    list_reminder_presets,
    set_cashing_rate,
    set_cashing_schedule_rule,
    set_driver_salary_preset,
    set_reminder_preset,
    set_reporting_baseline_date,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


PRESET_LABELS = {
    "NORMAL_DAY": "Normal day",
    "SUNDAY": "Sunday",
    "MAINTENANCE_WARNING_DAYS": "Maintenance",
    "DOCUMENT_EXPIRY_WARNING_DAYS": "Documents",
    "OVERDUE_CASHING_WARNING_DAYS": "Overdue cashing",
}

DAY_LABELS = {
    1: "Mon",
    2: "Tue",
    3: "Wed",
    4: "Thu",
    5: "Fri",
    6: "Sat",
    7: "Sun",
}


def _show_save_result(callback, *args, **kwargs) -> None:
    try:
        callback(*args, **kwargs)
        st.cache_data.clear()
        st.success("Preset saved.", icon=":material/check_circle:")
    except Exception as exc:
        st.error(f"Could not save preset: {exc}", icon=":material/error:")


st.subheader("Business Presets")
section = st.segmented_control(
    "Preset section",
    ["Cashing", "Schedule", "Salaries", "Reminders", "Reporting"],
    default="Cashing",
    label_visibility="collapsed",
)

try:
    if section == "Cashing":
        rates = list_cashing_rates()
        active_rates = {rate["rate_type"]: rate for rate in rates if rate["active"]}

        for rate_type in ("NORMAL_DAY", "SUNDAY"):
            rate = active_rates.get(rate_type)
            with st.container(border=True):
                st.markdown(f"**{PRESET_LABELS[rate_type]}**")
                if rate:
                    st.metric("Current rate", format_whole_kwacha(rate["amount"]))
                    st.caption(f"Active from {format_date(rate['effective_from'])}")
                else:
                    st.warning("No active rate configured.", icon=":material/warning:")

                with st.form(f"rate_{rate_type}", clear_on_submit=True):
                    amount = st.number_input(
                        "New rate (K)",
                        min_value=0.0,
                        value=float(rate["amount"]) if rate else 0.0,
                        step=50.0,
                        key=f"rate_amount_{rate_type}",
                    )
                    effective_from = st.date_input(
                        "Effective from",
                        value=today_lusaka() + timedelta(days=1),
                        format="DD/MM/YYYY",
                        key=f"rate_date_{rate_type}",
                    )
                    notes = st.text_input("Notes", key=f"rate_notes_{rate_type}")
                    if st.form_submit_button("Save rate", icon=":material/save:", type="primary"):
                        _show_save_result(set_cashing_rate, rate_type, amount, effective_from, notes)

        if rates:
            st.subheader("Rate history")
            for rate in rates[:8]:
                status = "Active" if rate["active"] else "Historical"
                st.caption(
                    f"{PRESET_LABELS[rate['rate_type']]} | {format_whole_kwacha(rate['amount'])} | "
                    f"{status} | {format_date(rate['effective_from'])} to {format_date(rate['effective_to'])}"
                )

    elif section == "Schedule":
        rules = list_cashing_schedule_rules()
        if rules:
            for rule in rules:
                covered = ", ".join(DAY_LABELS[day] for day in rule["covered_days"])
                with st.container(border=True):
                    st.markdown(f"**{DAY_LABELS[rule['collection_day']]} collection**")
                    st.caption(f"Covers {covered}")
                    if rule["include_previous_sunday"]:
                        st.caption("Includes optional previous Sunday amount")
                    if rule["notes"]:
                        st.write(rule["notes"])
                    with st.form(f"schedule_{rule['id']}", clear_on_submit=True):
                        selected_days = st.multiselect(
                            "Covered days",
                            list(DAY_LABELS.values()),
                            default=[DAY_LABELS[day] for day in rule["covered_days"]],
                            key=f"covered_days_{rule['id']}",
                        )
                        include_previous_sunday = st.toggle(
                            "Include previous Sunday option",
                            value=bool(rule["include_previous_sunday"]),
                            key=f"include_sunday_{rule['id']}",
                        )
                        effective_from = st.date_input(
                            "Effective from",
                            value=today_lusaka() + timedelta(days=1),
                            format="DD/MM/YYYY",
                            key=f"schedule_effective_from_{rule['id']}",
                        )
                        notes = st.text_input(
                            "Notes",
                            value=rule["notes"] or "",
                            key=f"schedule_notes_{rule['id']}",
                        )
                        if st.form_submit_button("Save schedule", icon=":material/save:", type="primary"):
                            selected_numbers = [
                                number
                                for number, label in DAY_LABELS.items()
                                if label in selected_days
                            ]
                            _show_save_result(
                                set_cashing_schedule_rule,
                                rule["collection_day"],
                                selected_numbers,
                                include_previous_sunday,
                                effective_from,
                                notes,
                            )
        else:
            empty_state("No schedule rules", "Add schedule rules before using overdue reminders.", ":material/event:")

    elif section == "Salaries":
        salary_presets = list_driver_salary_presets()
        drivers = get_drivers_overview()
        driver_options = {"Default salary": None}
        driver_options.update({driver["full_name"]: driver["id"] for driver in drivers})

        active_default = next(
            (preset for preset in salary_presets if preset["active"] and preset["driver_id"] is None),
            None,
        )
        with st.container(border=True):
            st.markdown("**Salary preset**")
            if active_default:
                st.metric("Default monthly salary", format_whole_kwacha(active_default["monthly_salary"]))
                st.caption(f"Active from {format_date(active_default['effective_from'])}")

            with st.form("salary_preset_form", clear_on_submit=True):
                driver_label = st.selectbox("Applies to", list(driver_options), index=0)
                monthly_salary = st.number_input(
                    "Monthly salary (K)",
                    min_value=0.0,
                    value=float(active_default["monthly_salary"]) if active_default else 2000.0,
                    step=100.0,
                )
                effective_from = st.date_input(
                    "Effective from",
                    value=today_lusaka() + timedelta(days=1),
                    format="DD/MM/YYYY",
                    key="salary_effective_from",
                )
                notes = st.text_input("Notes", key="salary_notes")
                if st.form_submit_button("Save salary preset", icon=":material/save:", type="primary"):
                    _show_save_result(
                        set_driver_salary_preset,
                        monthly_salary,
                        effective_from,
                        driver_options[driver_label],
                        notes,
                    )

        if salary_presets:
            st.subheader("Salary history")
            for preset in salary_presets[:8]:
                target = preset["driver_name"] or "Default salary"
                status = "Active" if preset["active"] else "Historical"
                st.caption(
                    f"{target} | {format_whole_kwacha(preset['monthly_salary'])} | "
                    f"{status} | {format_date(preset['effective_from'])} to {format_date(preset['effective_to'])}"
                )

    elif section == "Reminders":
        reminders = list_reminder_presets()
        for preset in reminders:
            label = PRESET_LABELS[preset["preset_key"]]
            with st.container(border=True):
                st.markdown(f"**{label}**")
                with st.form(f"reminder_{preset['preset_key']}"):
                    warning_days = st.number_input(
                        "Warning days",
                        min_value=0,
                        value=int(preset["warning_days"]),
                        step=1,
                        key=f"warning_days_{preset['preset_key']}",
                    )
                    active = st.toggle(
                        "Active",
                        value=bool(preset["active"]),
                        key=f"warning_active_{preset['preset_key']}",
                    )
                    notes = st.text_input(
                        "Notes",
                        value=preset["notes"] or "",
                        key=f"warning_notes_{preset['preset_key']}",
                    )
                    if st.form_submit_button("Save reminder", icon=":material/save:", type="primary"):
                        _show_save_result(
                            set_reminder_preset,
                            preset["preset_key"],
                            warning_days,
                            active,
                            notes,
                        )

    else:
        settings = get_business_settings()
        baseline = settings.get("REPORTING_BASELINE_DATE")
        collection_destination = settings.get("DEFAULT_COLLECTION_ACCOUNT_TYPE")

        st.info("Cashing collections are locked to Airtel Money for now.", icon=":material/mobile_friendly:")
        with st.container(border=True):
            st.markdown("**Reporting baseline**")
            current_value = baseline["setting_value"] if baseline else "2026-10-01"
            with st.form("reporting_baseline_form"):
                baseline_date = st.date_input(
                    "Start date",
                    value=date.fromisoformat(current_value),
                    format="DD/MM/YYYY",
                )
                notes = st.text_input("Notes", value=baseline["notes"] or "" if baseline else "")
                if st.form_submit_button("Save baseline", icon=":material/save:", type="primary"):
                    _show_save_result(set_reporting_baseline_date, baseline_date, notes)

        if collection_destination:
            st.caption(
                f"Collection account type: {collection_destination['setting_value'].replace('_', ' ').title()}"
            )
except Exception as exc:
    st.error(f"Business presets are not ready yet: {exc}", icon=":material/error:")

