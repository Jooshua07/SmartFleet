import streamlit as st

from components.cards import empty_state
from components.layout import fixed_page_controls
from components.reporting_period import period_controls
from services.dashboard_service import get_financial_summary, get_recent_activity
from services.finance_service import (
    get_collections,
    get_expenses,
    get_period_balance,
    get_period_ledger,
)
from utils.formatting import format_date, format_whole_kwacha
from services.preset_service import get_reporting_baseline_date
from utils.dates import today_lusaka


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_finance_general(start_date, end_date):
    return {
        "summary": get_financial_summary(start_date, end_date),
        "cash": get_period_balance(start_date, end_date),
        "activity": get_recent_activity(limit=8),
    }


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_collections(start_date, end_date):
    return get_collections(start_date, end_date)


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_expenses(start_date, end_date):
    return get_expenses(start_date, end_date)


@st.cache_data(ttl=15, max_entries=16, show_spinner=False)
def _load_balances(start_date, end_date):
    return {
        "business_balance": get_period_balance(start_date, end_date),
        "ledger": get_period_ledger(start_date, end_date),
    }


with fixed_page_controls():
    selected_section = st.segmented_control(
        "Finance section",
        ["General", "Collections", "Expenses", "Balances"],
        default="General",
        key="finance_section",
        label_visibility="collapsed",
    )

if selected_section == 'Balances':
    current_balance = get_period_balance(get_reporting_baseline_date(), today_lusaka())
    st.metric('Business Balance Now', format_whole_kwacha(current_balance['closing_balance']), border=True)

start_date, end_date = period_controls('finance')
st.caption(f"{format_date(start_date)} to {format_date(end_date)}")

if selected_section == "General":
    finance_data = _load_finance_general(start_date, end_date)
    summary = finance_data["summary"]
    cash = finance_data['cash']
    with st.container(horizontal=True):
        st.metric("Collections", format_whole_kwacha(summary["revenue"]), border=True)
        st.metric("Operating Costs", format_whole_kwacha(summary["expenses"]), border=True)
        st.metric("Other Payments", format_whole_kwacha(cash['other_payments']), border=True)
    with st.expander('Other payments breakdown'):
        for kind, amount in cash['other_payment_breakdown'].items():
            st.write(f"{kind.replace('_', ' ').title()}: {format_whole_kwacha(amount)}")
    st.caption("Recorded operating costs exclude loan principal repayments, owner drawings and recoverable advances.")

    st.subheader("Recent Activity")
    activity = [item for item in finance_data["activity"] if start_date <= item['activity_date'] <= end_date]
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
    balance_data = _load_balances(start_date, end_date)
    business_balance = balance_data["business_balance"]

    with st.container(horizontal=True):
        st.metric("Money Received", format_whole_kwacha(business_balance["money_in"]), border=True)
        st.metric("Money Paid Out", format_whole_kwacha(business_balance["money_out"]), border=True)

    st.caption(
        "Loan repayments are financing payments, so they reduce Business Balance without being mixed into operating expenses."
    )

    ledger = balance_data["ledger"]
    if ledger:
        st.subheader("Business ledger")
        for item in ledger:
            with st.container(border=True):
                st.markdown(f"**{item['description'] or item['transaction_type']}**")
                st.caption(
                    f"{format_date(item['transaction_date'])} | {item['transaction_type']}"
                )
                st.markdown(format_whole_kwacha(item['amount'] if item['direction'] == 'IN' else -item['amount']))
    else:
        empty_state("No ledger entries", "Recorded money movements will appear here.", ":material/receipt_long:")
