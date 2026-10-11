import pandas as pd
import streamlit as st

from components.cards import empty_state
from services.dashboard_service import (
    get_bus_performance,
    get_bus_status_counts,
    get_financial_summary,
    get_recent_activity,
)
from services.reminder_service import get_open_reminders
from utils.dates import period_bounds
from utils.formatting import format_date, format_whole_kwacha


mode = st.segmented_control("Reporting period", ["Week", "Month"], default="Week")
start_date, end_date = period_bounds(mode)
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

with st.skeleton(height=120):
    summary = get_financial_summary(start_date, end_date)

with st.container(horizontal=True):
    st.metric(
        "Total Revenue",
        format_whole_kwacha(summary["revenue"]),
        border=True,
        icon=":material/bar_chart:",
    )
    st.metric(
        "Total Expenses",
        format_whole_kwacha(summary["expenses"]),
        border=True,
        icon=":material/account_balance_wallet:",
    )

counts = get_bus_status_counts()
with st.container(border=True):
    if counts["TOTAL"] == 0:
        st.info("No buses registered yet.", icon=":material/directions_bus:")
    elif counts["INACTIVE"] == 0:
        st.success("ALL BUSES ACTIVE", icon=":material/check_circle:")
    else:
        st.write(f"{counts['ACTIVE']} buses active | {counts['INACTIVE']} buses deactivated")

st.subheader("Bus revenue vs expenses")
performance = get_bus_performance(start_date, end_date)
if performance:
    chart_data = pd.DataFrame(performance)
    chart_data = chart_data.rename(
        columns={"registration_number": "Bus", "revenue": "Revenue", "expenses": "Expenses"}
    )
    st.bar_chart(
        chart_data,
        x="Bus",
        y=["Revenue", "Expenses"],
        y_label="ZMW",
        stack=False,
        alt="Revenue and expenses by registered bus for the selected period",
    )
else:
    empty_state(
        "No bus performance yet",
        "Register buses and record cashing or expenses to populate this chart.",
        ":material/bar_chart:",
    )

with st.container(border=True):
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        st.subheader("Alerts and reminders")
        if st.button("View All", icon=":material/chevron_right:"):
            st.switch_page("app_pages/reminders.py")

    reminders = get_open_reminders(limit=3)
    if reminders:
        for reminder in reminders:
            st.write(f"**{reminder['title']}**")
            st.caption(f"{reminder['reminder_type']} due {format_date(reminder['due_date'])}")
    else:
        st.caption("No pending reminders.")

with st.container(border=True):
    st.subheader("Recent Activity")
    activity = get_recent_activity(limit=5)
    if activity:
        for item in activity:
            st.write(f"**{item['title']}**")
            st.caption(f"{item['detail']} - {format_date(item['activity_date'])}")
    else:
        st.caption("No recorded activity yet.")

