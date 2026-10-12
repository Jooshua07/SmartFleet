import streamlit as st

from components.cards import empty_state
from services.dashboard_service import (
    get_activity_date_bounds,
    get_bus_performance,
    get_bus_status_counts,
    get_financial_summary,
    get_recent_activity,
)
from services.reminder_service import get_open_reminders
from services.validation_service import get_data_validation_warnings
from utils.dashboard_charts import build_bus_performance_chart, build_bus_performance_chart_data
from utils.dates import subtract_months, today_lusaka
from utils.formatting import format_date, format_whole_kwacha


def _selected_period_bounds():
    today = today_lusaka()
    mode = st.segmented_control("Period", ["1 month", "3 months", "Custom"], default="1 month", key="home_period")
    if mode == "1 month":
        return subtract_months(today, 1), today
    if mode == "3 months":
        return subtract_months(today, 3), today

    custom_mode = st.segmented_control(
        "Custom period",
        ["All time", "6 months", "Choose dates"],
        default="All time",
        key="home_custom_period",
    )
    if custom_mode == "All time":
        bounds = get_activity_date_bounds()
        return bounds["earliest_date"] or today, today
    if custom_mode == "6 months":
        return subtract_months(today, 6), today

    start = st.date_input(
        "Start date",
        value=subtract_months(today, 1),
        format="DD/MM/YYYY",
        key="home_custom_start",
    )
    end = st.date_input(
        "End date",
        value=today,
        format="DD/MM/YYYY",
        key="home_custom_end",
    )
    if start > end:
        st.error("Start date must be before end date.", icon=":material/error:")
        st.stop()
    return start, end


start_date, end_date = _selected_period_bounds()
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

with st.skeleton(height=120):
    summary = get_financial_summary(start_date, end_date)

with st.container(horizontal=True):
    st.metric(
        "Revenue",
        format_whole_kwacha(summary["revenue"]),
        border=True,
        icon=":material/bar_chart:",
    )
    st.metric(
        "Expenses",
        format_whole_kwacha(summary["expenses"]),
        border=True,
        icon=":material/account_balance_wallet:",
    )
    st.metric(
        "Profit",
        format_whole_kwacha(summary["revenue"] - summary["expenses"]),
        border=True,
        icon=":material/trending_up:",
    )

warnings = get_data_validation_warnings()
if warnings:
    with st.container(border=True):
        st.subheader("Setup checks")
        for warning in warnings[:4]:
            st.warning(warning, icon=":material/warning:")
        if len(warnings) > 4:
            st.caption(f"{len(warnings) - 4} more checks in More.")

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
    chart_data = build_bus_performance_chart_data(performance)
    st.altair_chart(
        build_bus_performance_chart(chart_data),
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
