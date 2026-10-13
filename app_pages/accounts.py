import pandas as pd
import streamlit as st

from components.cards import empty_state
from services.bus_account_service import get_bus_account_detail, get_bus_contribution_summary
from utils.dashboard_charts import build_bus_performance_chart, build_bus_performance_chart_data
from utils.dates import subtract_months, today_lusaka
from utils.formatting import format_date, format_whole_kwacha


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_bus_accounts(start_date, end_date):
    return get_bus_contribution_summary(start_date, end_date)


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_bus_detail(bus_id, start_date, end_date):
    return get_bus_account_detail(bus_id, start_date, end_date)


def _selected_period_bounds():
    today = today_lusaka()
    mode = st.segmented_control("Period", ["1 Month", "3 Months", "Custom"], default="1 Month")
    if mode == "1 Month":
        return subtract_months(today, 1), today
    if mode == "3 Months":
        return subtract_months(today, 3), today

    with st.container(horizontal=True):
        start = st.date_input("Start date", value=subtract_months(today, 1), format="DD/MM/YYYY")
        end = st.date_input("End date", value=today, format="DD/MM/YYYY")
    if start > end:
        st.error("Start date must be before end date.", icon=":material/error:")
        st.stop()
    return start, end


st.subheader("Bus Accounts")

start_date, end_date = _selected_period_bounds()
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

data = _load_bus_accounts(start_date, end_date)
buses = data["buses"]

with st.container(horizontal=True):
    st.metric(
        "Shared business costs",
        format_whole_kwacha(data["shared_general_costs"]),
        border=True,
    )
    total_contribution = sum(row["recorded_contribution"] for row in buses)
    st.metric("Recorded bus contribution", format_whole_kwacha(total_contribution), border=True)

st.caption(
    "Recorded Bus Contribution uses bus-attributed cashing and bus-attributed operating costs only. "
    "Shared business costs are shown separately and are not divided across buses."
)

if buses:
    chart_rows = [
        {
            "registration_number": row["registration_number"],
            "revenue": row["recorded_revenue"],
            "expenses": row["attributed_costs"],
        }
        for row in buses
    ]
    chart_data = build_bus_performance_chart_data(chart_rows)
    st.altair_chart(
        build_bus_performance_chart(chart_data),
        alt="Recorded revenue and attributed operating costs by bus",
    )

    st.subheader("Bus comparison")
    for row in buses:
        with st.container(border=True):
            st.markdown(f"**{row['registration_number']}**")
            if row["estimated_revenue"]:
                st.caption("Some cashing allocation is estimated or adjusted, not confirmed actual.")
            with st.container(horizontal=True):
                st.metric("Revenue", format_whole_kwacha(row["recorded_revenue"]), border=True)
                st.metric("Costs", format_whole_kwacha(row["attributed_costs"]), border=True)
                st.metric("Contribution", format_whole_kwacha(row["recorded_contribution"]), border=True)

    options = {row["registration_number"]: row["bus_id"] for row in buses}
    selected_registration = st.selectbox("Bus detail", list(options), key="bus_accounts_selected_bus")
    selected_bus_id = options[selected_registration]
    detail = _load_bus_detail(selected_bus_id, start_date, end_date)

    selected_summary = next(row for row in buses if row["bus_id"] == selected_bus_id)
    st.subheader(f"{selected_registration} detail")
    with st.container(horizontal=True):
        st.metric("Revenue", format_whole_kwacha(selected_summary["recorded_revenue"]), border=True)
        st.metric("Attributed costs", format_whole_kwacha(selected_summary["attributed_costs"]), border=True)
        st.metric("Recorded contribution", format_whole_kwacha(selected_summary["recorded_contribution"]), border=True)

    trend = detail["trend"]
    if trend:
        trend_df = pd.DataFrame(trend).rename(
            columns={
                "month": "Month",
                "recorded_revenue": "Recorded Revenue",
                "attributed_costs": "Attributed Costs",
                "recorded_contribution": "Recorded Contribution",
            }
        )
        for column in ["Recorded Revenue", "Attributed Costs", "Recorded Contribution"]:
            trend_df[column] = trend_df[column].astype(float)
        st.line_chart(
            trend_df,
            x="Month",
            y=["Recorded Revenue", "Attributed Costs"],
            alt=f"Revenue and cost trend for {selected_registration}",
        )
    else:
        st.caption("No monthly trend yet for this bus in the selected period.")

    costs_by_category = detail["costs_by_category"]
    if costs_by_category:
        category_df = pd.DataFrame(costs_by_category).rename(
            columns={"category_name": "Category", "amount": "Amount"}
        )
        category_df["Amount"] = category_df["Amount"].astype(float)
        st.bar_chart(
            category_df,
            x="Category",
            y="Amount",
            alt=f"Costs by category for {selected_registration}",
        )
    else:
        st.caption("No bus-attributed costs in this period.")

    st.subheader("Recent bus-related transactions")
    recent = detail["recent_transactions"]
    if recent:
        for item in recent:
            with st.container(border=True):
                st.markdown(f"**{item['title']}**")
                st.caption(f"{format_date(item['transaction_date'])} | {item['transaction_group']} | {item['detail']}")
                st.markdown(format_whole_kwacha(item["amount"]))
    else:
        st.caption("No bus-related transactions in this period.")
else:
    empty_state("No buses yet", "Register buses to compare bus accounts.", ":material/directions_bus:")
