from datetime import date

import streamlit as st

from components.cards import empty_state
from services.driver_money_service import (
    cancel_driver_salary,
    get_driver_money_detail,
    get_salary_preview,
    list_driver_money_profiles,
    record_driver_advance,
    record_driver_salary,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


def _profile_label(profile: dict) -> str:
    bus = profile["assigned_bus"] or "No bus"
    return f"{profile['driver_name']} | {bus} | {profile['employment_status']}"


st.subheader("Driver Money")

profiles = list_driver_money_profiles()
if not profiles:
    empty_state("No drivers", "Add drivers before recording salary or advances.", ":material/person:")
    st.stop()

profile_options = {_profile_label(profile): profile["employment_id"] for profile in profiles}
selected_profile = st.selectbox("Driver", list(profile_options), key="driver_money_profile")
employment_id = profile_options[selected_profile]
detail = get_driver_money_detail(employment_id)
employment = detail["employment"]

with st.container(border=True):
    st.markdown(f"**{employment['driver_name']}**")
    st.caption(
        f"Employment: {format_date(employment['start_date'])} to {format_date(employment['end_date'])} | "
        f"{employment['employment_status']}"
    )

mode = st.segmented_control(
    "Driver money action",
    ["Record Salary", "Record Advance", "History"],
    default="Record Salary",
    key="driver_money_mode",
)

today = today_lusaka()

if mode == "Record Advance":
    with st.form("driver_advance_form", clear_on_submit=True):
        advance_date = st.date_input("Advance date", value=today, format="DD/MM/YYYY")
        amount = st.number_input("Advance amount (K)", min_value=0.0, value=0.0, step=50.0)
        reason = st.text_input("Reason", placeholder="Optional")
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save advance", icon=":material/payments:", type="primary")
    if submitted:
        try:
            record_driver_advance(employment_id, advance_date, amount, reason, notes)
            st.cache_data.clear()
            st.success("Advance recorded.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record advance: {exc}", icon=":material/error:")

elif mode == "Record Salary":
    salary_year = st.number_input("Salary year", min_value=2026, value=today.year, step=1)
    salary_month = st.selectbox(
        "Salary month",
        list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda value: date(int(salary_year), value, 1).strftime("%B"),
    )
    other_deductions = st.number_input("Other deductions (K)", min_value=0.0, value=0.0, step=50.0)

    try:
        preview = get_salary_preview(employment_id, int(salary_year), int(salary_month), other_deductions)
        with st.container(horizontal=True):
            st.metric("Gross earned", format_whole_kwacha(preview["prorated_salary"]), border=True)
            st.metric("Suggested recovery", format_whole_kwacha(preview["suggested_recovery"]), border=True)
            st.metric("Net payment", format_whole_kwacha(preview["net_salary"]), border=True)
        st.caption(
            f"{preview['worked_days']} of {preview['days_in_month']} days counted for this payroll month."
        )
    except Exception as exc:
        preview = None
        st.error(f"Salary preview is not ready: {exc}", icon=":material/error:")

    if preview:
        with st.form("driver_salary_form", clear_on_submit=True):
            payment_date = st.date_input("Payment date", value=today, format="DD/MM/YYYY")
            recovery = st.number_input(
                "Advance recovery (K)",
                min_value=0.0,
                value=float(preview["suggested_recovery"]),
                step=50.0,
            )
            notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Save salary", icon=":material/save:", type="primary")
        if submitted:
            try:
                record_driver_salary(
                    employment_id,
                    int(salary_year),
                    int(salary_month),
                    payment_date,
                    recovery_amount=recovery,
                    other_deductions=other_deductions,
                    notes=notes,
                )
                st.cache_data.clear()
                st.success("Salary recorded.", icon=":material/check_circle:")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not record salary: {exc}", icon=":material/error:")

else:
    pass

st.subheader("Outstanding advances")
open_advances = [row for row in detail["advances"] if row["outstanding_amount"] > 0]
if open_advances:
    for advance in open_advances:
        with st.container(border=True):
            st.markdown(format_whole_kwacha(advance["outstanding_amount"]))
            st.caption(
                f"Advanced {format_whole_kwacha(advance['amount'])} on {format_date(advance['advance_date'])} | "
                f"Recovered {format_whole_kwacha(advance['recovered_amount'])}"
            )
            if advance["reason"]:
                st.write(advance["reason"])
else:
    st.caption("No outstanding advances for this driver.")

st.subheader("Salary history")
if detail["salaries"]:
    for salary in detail["salaries"][:8]:
        with st.container(border=True):
            st.markdown(
                f"**{date(salary['salary_year'], salary['salary_month'], 1).strftime('%B %Y')}**"
            )
            st.caption(
                f"{salary['status']} | Paid {format_date(salary['payment_date'])} | "
                f"Gross {format_whole_kwacha(salary['prorated_salary'])} | "
                f"Advance recovery {format_whole_kwacha(salary['advance_recovery'])} | "
                f"Net {format_whole_kwacha(salary['net_salary'])}"
            )
            if st.button("Cancel salary", icon=":material/cancel:", key=f"cancel_salary_{salary['id']}"):
                try:
                    cancel_driver_salary(salary["id"])
                    st.cache_data.clear()
                    st.success("Salary cancelled.", icon=":material/check_circle:")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not cancel salary: {exc}", icon=":material/error:")
else:
    st.caption("No salary records yet.")

if detail["recoveries"]:
    st.subheader("Recovery history")
    for recovery in detail["recoveries"][:8]:
        st.caption(
            f"{date(recovery['salary_year'], recovery['salary_month'], 1).strftime('%b %Y')} | "
            f"{format_whole_kwacha(recovery['amount'])} | {recovery['salary_status']}"
        )
