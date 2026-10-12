import pandas as pd
import streamlit as st

from services.report_service import get_balance_export, get_collection_export, get_expense_export
from utils.dates import month_bounds, today_lusaka, week_bounds
from utils.formatting import format_date


def _csv_download(label: str, rows: list[dict], filename: str) -> None:
    if not rows:
        st.caption(f"No {label.lower()} records for this period.")
        return
    data = pd.DataFrame(rows)
    csv_bytes = data.to_csv(index=False).encode("utf-8")
    st.download_button(
        label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )


st.subheader("Reports")

today = today_lusaka()
period = st.segmented_control("Period", ["Week", "Month", "Custom"], default="Week")
if period == "Month":
    start_date, end_date = month_bounds(today)
elif period == "Custom":
    start_date = st.date_input("Start date", value=today, format="DD/MM/YYYY")
    end_date = st.date_input("End date", value=today, format="DD/MM/YYYY")
else:
    start_date, end_date = week_bounds(today)

if start_date > end_date:
    st.error("Start date must be before end date.", icon=":material/error:")
    st.stop()

st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

collections = get_collection_export(start_date, end_date)
expenses = get_expense_export(start_date, end_date)
balances = get_balance_export()

with st.container(border=True):
    st.markdown("**Collections export**")
    _csv_download("Download collections CSV", collections, f"smartfleet_collections_{start_date}_{end_date}.csv")

with st.container(border=True):
    st.markdown("**Expenses export**")
    _csv_download("Download expenses CSV", expenses, f"smartfleet_expenses_{start_date}_{end_date}.csv")

with st.container(border=True):
    st.markdown("**Balances export**")
    _csv_download("Download balances CSV", balances, "smartfleet_balances.csv")
