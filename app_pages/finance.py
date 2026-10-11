import streamlit as st

from components.cards import empty_state
from services.dashboard_service import get_financial_summary, get_recent_activity
from services.finance_service import get_account_balances, get_collections, get_expenses
from utils.dates import period_bounds
from utils.formatting import format_date, format_whole_kwacha


tab_general, tab_collections, tab_expenses, tab_balances = st.tabs(
    ["General", "Collections", "Expenses", "Balances"]
)

mode = st.segmented_control("Reporting period", ["Week", "Month"], default="Week")
start_date, end_date = period_bounds(mode)
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

with tab_general:
    summary = get_financial_summary(start_date, end_date)
    with st.container(horizontal=True):
        st.metric("Total Collections", format_whole_kwacha(summary["revenue"]), border=True)
        st.metric("Total Expenses", format_whole_kwacha(summary["expenses"]), border=True)
        st.metric("Pending Remittances", format_whole_kwacha(summary["pending_remittances"]), border=True)

    st.subheader("Recent Activity")
    activity = get_recent_activity(limit=8)
    if activity:
        for item in activity:
            st.write(f"**{item['title']}**")
            st.caption(f"{format_date(item['activity_date'])} | {format_whole_kwacha(item['amount'])}")
    else:
        st.caption("No finance activity for this period.")

with tab_collections:
    collections = get_collections(start_date, end_date)
    if collections:
        for item in collections:
            with st.container(border=True):
                st.markdown(f"**{format_date(item['collection_date'])}**")
                st.caption(f"{item['bus_count']} bus entries")
                st.markdown(format_whole_kwacha(item["total_amount"]))
    else:
        empty_state("No collections", "No recorded collections for this period.", ":material/payments:")

with tab_expenses:
    expenses = get_expenses(start_date, end_date)
    if expenses:
        for item in expenses:
            with st.container(border=True):
                st.markdown(f"**{item['category_name']}**")
                target = item["registration_number"] or item["scope"].replace("_", " ").title()
                st.caption(f"{format_date(item['expense_date'])} | {target}")
                st.markdown(format_whole_kwacha(item["amount"]))
    else:
        empty_state("No expenses", "No recorded expenses for this period.", ":material/receipt_long:")

with tab_balances:
    st.warning(
        "Balances are calculated from opening balances and recorded ledger transactions only. "
        "They are not profit and do not include unrecorded cash.",
        icon=":material/warning:",
    )
    balances = get_account_balances()
    if balances:
        for account in balances:
            with st.container(border=True):
                st.markdown(f"**{account['name']}**")
                st.caption(account["account_type"])
                st.metric("Calculated balance", format_whole_kwacha(account["calculated_balance"]))
    else:
        empty_state("No active accounts", "No active financial accounts are configured.", ":material/account_balance:")

