import streamlit as st

from components.cards import empty_state
from components.layout import fixed_page_controls
from services.dashboard_service import get_financial_summary, get_recent_activity
from services.finance_service import (
    get_business_balance,
    get_business_ledger,
    get_collections,
    get_expenses,
)
from utils.dates import period_bounds
from utils.formatting import format_date, format_whole_kwacha


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_finance_general(start_date, end_date):
    return {
        "summary": get_financial_summary(start_date, end_date),
        "activity": get_recent_activity(limit=8),
    }


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_collections(start_date, end_date):
    return get_collections(start_date, end_date)


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_expenses(start_date, end_date):
    return get_expenses(start_date, end_date)


@st.cache_data(ttl=15, max_entries=16, show_spinner=False)
def _load_balances():
    return {
        "business_balance": get_business_balance(),
        "ledger": get_business_ledger(limit=20),
    }


with fixed_page_controls():
    selected_section = st.segmented_control(
        "Finance section",
        ["General", "Collections", "Expenses", "Balances"],
        default="General",
        key="finance_section",
        label_visibility="collapsed",
    )

mode = st.segmented_control("Reporting period", ["Week", "Month"], default="Week")
start_date, end_date = period_bounds(mode)
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

if selected_section == "General":
    finance_data = _load_finance_general(start_date, end_date)
    summary = finance_data["summary"]
    with st.container(horizontal=True):
        st.metric("Recorded revenue", format_whole_kwacha(summary["revenue"]), border=True)
        st.metric("Recorded operating costs", format_whole_kwacha(summary["expenses"]), border=True)
        st.metric("Pending Remittances", format_whole_kwacha(summary["pending_remittances"]), border=True)
    st.caption("Recorded operating costs exclude loan principal repayments, owner drawings and recoverable advances.")

    st.subheader("Recent Activity")
    activity = finance_data["activity"]
    if activity:
        for item in activity:
            st.write(f"**{item['title']}**")
            st.caption(f"{format_date(item['activity_date'])} | {format_whole_kwacha(item['amount'])}")
    else:
        st.caption("No finance activity for this period.")

elif selected_section == "Collections":
    collections = _load_collections(start_date, end_date)
    if collections:
        for item in collections:
            with st.container(border=True):
                st.markdown(f"**{format_date(item['collection_date'])}**")
                st.caption(f"{item['bus_count']} bus entries")
                st.markdown(format_whole_kwacha(item["total_amount"]))
    else:
        empty_state("No collections", "No recorded collections for this period.", ":material/payments:")

elif selected_section == "Expenses":
    expenses = _load_expenses(start_date, end_date)
    if expenses:
        for item in expenses:
            with st.container(border=True):
                st.markdown(f"**{item['description']}**")
                target = item["registration_number"] or item["scope"].replace("_", " ").title()
                st.caption(f"{format_date(item['expense_date'])} | {item['category_name']} | {target}")
                st.markdown(format_whole_kwacha(item["amount"]))
    else:
        empty_state("No expenses", "No recorded expenses for this period.", ":material/receipt_long:")

else:
    balance_data = _load_balances()
    business_balance = balance_data["business_balance"]

    st.metric(
        "Business Balance",
        format_whole_kwacha(business_balance["business_balance"]),
        border=True,
    )
    st.caption(f"From reporting baseline {format_date(business_balance['baseline_date'])}")

    with st.container(horizontal=True):
        st.metric("Money in", format_whole_kwacha(business_balance["money_in"]), border=True)
        st.metric("Money out", format_whole_kwacha(business_balance["money_out"]), border=True)

    st.caption(
        "Loan repayments are financing payments, so they reduce Business Balance without being mixed into operating expenses."
    )

    ledger = balance_data["ledger"]
    if ledger:
        st.subheader("Business ledger")
        for item in ledger:
            with st.container(border=True):
                st.markdown(f"**{item['description'] or item['classification']}**")
                st.caption(
                    f"{format_date(item['transaction_date'])} | {item['classification']} | {item['transaction_type']}"
                )
                st.markdown(format_whole_kwacha(item["signed_amount"]))
    else:
        empty_state("No ledger entries", "Recorded money movements will appear here.", ":material/receipt_long:")
