import streamlit as st

from components.cards import empty_state
from services.dashboard_service import (
    get_activity_date_bounds,
    get_bus_status_counts,
    get_financial_summary,
    get_recent_activity,
)
from services.performance_service import get_business_performance_series
from services.preset_service import get_reporting_baseline_date
from services.reminder_service import get_open_reminders
from services.validation_service import get_data_validation_warnings
from utils.dashboard_charts import build_business_performance_chart, build_business_performance_chart_data
from utils.dates import subtract_months, today_lusaka
from utils.formatting import format_date, format_whole_kwacha


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_home_data(start_date, end_date):
    return {
        "summary": get_financial_summary(start_date, end_date),
        "warnings": get_data_validation_warnings(),
        "counts": get_bus_status_counts(),
        "reminders": get_open_reminders(limit=3),
        "activity": get_recent_activity(limit=5),
    }


@st.cache_data(ttl=60, max_entries=12, show_spinner=False)
def _load_activity_bounds():
    return get_activity_date_bounds()


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
        bounds = _load_activity_bounds()
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


@st.cache_data(ttl=30, max_entries=32, show_spinner=False)
def _load_performance_series(start_date, end_date, grouping):
    return get_business_performance_series(start_date, end_date, grouping)


def _chart_bounds():
    today = today_lusaka()
    baseline = get_reporting_baseline_date()
    mode = st.segmented_control(
        "Business performance period",
        ["Daily", "Weekly", "Date Range"],
        default="Daily",
        key="home_business_performance_period",
    )
    if mode == "Date Range":
        start = st.date_input(
            "Chart start",
            value=baseline,
            min_value=baseline,
            max_value=today,
            format="DD/MM/YYYY",
            key="home_business_chart_start",
        )
        end = st.date_input(
            "Chart end",
            value=today,
            min_value=baseline,
            max_value=today,
            format="DD/MM/YYYY",
            key="home_business_chart_end",
        )
        if start > end:
            st.error("Chart start date must be before chart end date.", icon=":material/error:")
            st.stop()
        return start, end, "Daily"
    return baseline, today, mode


start_date, end_date = _selected_period_bounds()
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

with st.skeleton(height=120):
    home_data = _load_home_data(start_date, end_date)
    summary = home_data["summary"]

with st.container(horizontal=True):
    st.metric(
        "Revenue",
        format_whole_kwacha(summary["revenue"]),
        border=True,
        icon=":material/bar_chart:",
    )
    st.metric(
        "Operating costs",
        format_whole_kwacha(summary["expenses"]),
        border=True,
        icon=":material/account_balance_wallet:",
    )
    st.metric(
        "Recorded margin",
        format_whole_kwacha(summary["revenue"] - summary["expenses"]),
        border=True,
        icon=":material/trending_up:",
    )
st.caption("Recorded margin excludes financing payments, owner drawings and recoverable advances.")

warnings = home_data["warnings"]
if warnings:
    with st.container(border=True):
        st.subheader("Setup checks")
        for warning in warnings[:4]:
            st.warning(warning, icon=":material/warning:")
        if len(warnings) > 4:
            st.caption(f"{len(warnings) - 4} more checks in More.")

counts = home_data["counts"]
with st.container(border=True):
    if counts["TOTAL"] == 0:
        st.info("No buses registered yet.", icon=":material/directions_bus:")
    elif counts["INACTIVE"] == 0:
        st.success("ALL BUSES ACTIVE", icon=":material/check_circle:")
    else:
        st.write(f"{counts['ACTIVE']} buses active | {counts['INACTIVE']} buses deactivated")

with st.container(border=True):
    st.subheader("Business Performance")
    chart_start, chart_end, chart_grouping = _chart_bounds()
    st.caption(f"{format_date(chart_start)} to {format_date(chart_end)}")
    series = _load_performance_series(chart_start, chart_end, chart_grouping)
    chart_data = build_business_performance_chart_data(series)
    if chart_data.empty or chart_data["Amount"].abs().sum() == 0:
        empty_state(
            "No performance records yet",
            "Record cashing, expenses or payroll to populate this chart.",
            ":material/monitoring:",
        )
    else:
        st.altair_chart(
            build_business_performance_chart(chart_data),
            alt="Recorded revenue, operating expenses and operating profit or loss over time",
        )

with st.container(border=True):
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        st.subheader("Alerts and reminders")
        if st.button("View All", icon=":material/chevron_right:"):
            st.switch_page("app_pages/reminders.py")

    reminders = home_data["reminders"]
    if reminders:
        for reminder in reminders:
            st.write(f"**{reminder['title']}**")
            st.caption(f"{reminder['reminder_type']} due {format_date(reminder['due_date'])}")
    else:
        st.caption("No pending reminders.")

with st.container(border=True):
    st.subheader("Recent Activity")
    activity = home_data["activity"]
    if activity:
        for item in activity:
            st.write(f"**{item['title']}**")
            st.caption(f"{item['detail']} - {format_date(item['activity_date'])}")
    else:
        st.caption("No recorded activity yet.")
