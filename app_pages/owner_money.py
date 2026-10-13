import streamlit as st

from services.loan_service import (
    cancel_owner_drawing,
    cancel_owner_loan_transaction,
    get_owner_money_summary,
    list_owner_money_activity,
    list_business_loans,
    record_business_repayment_to_owner,
    record_loan_repayment,
    record_owner_drawing,
    record_owner_loan_to_business,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


st.subheader("Owner Money")

summary = get_owner_money_summary()
with st.container(horizontal=True):
    st.metric("Owed to owner", format_whole_kwacha(summary["owner_balance"]), border=True)
    st.metric("Owner funded", format_whole_kwacha(summary["owner_funded"]), border=True)
    st.metric("Repaid to owner", format_whole_kwacha(summary["owner_repaid"]), border=True)

mode = st.segmented_control(
    "Owner money action",
    ["Owner Drawing", "Owner Loan to Business", "Owner Pays Business Loan", "Business Repays Owner"],
    default="Owner Drawing",
    key="owner_money_mode",
)

today = today_lusaka()

if mode == "Owner Drawing":
    with st.form("owner_drawing_form", clear_on_submit=True):
        transaction_date = st.date_input("Date", value=today, format="DD/MM/YYYY")
        amount = st.number_input("Amount (K)", min_value=0.0, value=0.0, step=100.0)
        reference = st.text_input("Reference", placeholder="Optional")
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save drawing", icon=":material/payments:", type="primary")
    if submitted:
        try:
            record_owner_drawing(transaction_date, amount, notes=notes, reference=reference)
            st.cache_data.clear()
            st.success("Owner drawing recorded.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record drawing: {exc}", icon=":material/error:")

elif mode == "Owner Loan to Business":
    with st.form("owner_loan_to_business_form", clear_on_submit=True):
        transaction_date = st.date_input("Date", value=today, format="DD/MM/YYYY")
        amount = st.number_input("Amount (K)", min_value=0.0, value=0.0, step=100.0)
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save owner loan", icon=":material/add:", type="primary")
    if submitted:
        try:
            record_owner_loan_to_business(transaction_date, amount, notes=notes)
            st.cache_data.clear()
            st.success("Owner loan recorded.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record owner loan: {exc}", icon=":material/error:")

elif mode == "Owner Pays Business Loan":
    loans = [loan for loan in list_business_loans() if loan["status"] == "ACTIVE"]
    loan_options = {"Unidentified loan": None}
    loan_options.update(
        {
            f"{loan['loan_name']} | {loan['lender']} | {format_whole_kwacha(loan['outstanding_principal'])} left": loan[
                "id"
            ]
            for loan in loans
        }
    )
    with st.form("owner_pays_loan_form", clear_on_submit=True):
        selected_loan = st.selectbox("Loan", list(loan_options))
        repayment_date = st.date_input("Date paid", value=today, format="DD/MM/YYYY")
        principal = st.number_input("Principal paid personally (K)", min_value=0.0, value=0.0, step=100.0)
        fees = st.number_input("Interest/fees paid personally (K)", min_value=0.0, value=0.0, step=50.0)
        paid_to = st.text_input("Paid to", placeholder="Lender or association")
        reference = st.text_input("Reference", placeholder="Optional")
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save personal payment", icon=":material/handshake:", type="primary")
    if submitted:
        try:
            record_loan_repayment(
                repayment_date,
                principal,
                "OWNER_PERSONAL",
                loan_id=loan_options[selected_loan],
                paid_to=paid_to,
                interest_or_fees=fees,
                reference=reference,
                notes=notes,
            )
            st.cache_data.clear()
            st.success("Owner-paid loan repayment recorded.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record owner-paid repayment: {exc}", icon=":material/error:")

else:
    with st.form("business_repays_owner_form", clear_on_submit=True):
        transaction_date = st.date_input("Date", value=today, format="DD/MM/YYYY")
        amount = st.number_input("Amount (K)", min_value=0.0, value=0.0, step=100.0)
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save repayment", icon=":material/payments:", type="primary")
    if submitted:
        try:
            record_business_repayment_to_owner(transaction_date, amount, notes=notes)
            st.cache_data.clear()
            st.success("Repayment to owner recorded.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not repay owner: {exc}", icon=":material/error:")

activity = list_owner_money_activity()
if activity:
    st.subheader("Owner money history")
    for item in activity:
        with st.container(border=True):
            st.caption(
                f"{format_date(item['transaction_date'])} | {item['label']} | "
                f"{format_whole_kwacha(item['amount'])} | {item['description']}"
            )
            with st.expander("Correction"):
                if item["linked_to_loan_repayment"]:
                    st.caption("Reverse this from Loans because it is linked to a business-loan repayment.")
                else:
                    with st.form(f"cancel_owner_money_{item['record_type']}_{item['record_id']}", clear_on_submit=True):
                        reason = st.text_input(
                            "Correction reason",
                            key=f"owner_money_reason_{item['record_type']}_{item['record_id']}",
                        )
                        submitted = st.form_submit_button("Cancel record", icon=":material/undo:")
                    if submitted:
                        try:
                            if item["record_type"] == "OWNER_DRAWING":
                                cancel_owner_drawing(item["record_id"], reason)
                            else:
                                cancel_owner_loan_transaction(item["record_id"], reason)
                            st.cache_data.clear()
                            st.success("Owner money record cancelled.", icon=":material/check_circle:")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not cancel record: {exc}", icon=":material/error:")
else:
    st.caption("No owner money transactions yet.")
