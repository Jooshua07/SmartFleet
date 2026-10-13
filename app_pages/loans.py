import streamlit as st

from components.cards import empty_state
from services.loan_service import (
    add_business_loan,
    cancel_loan_repayment,
    list_business_loans,
    list_loan_repayments,
    record_loan_repayment,
)
from utils.dates import today_lusaka
from utils.formatting import format_date, format_whole_kwacha


st.subheader("Loans")

loans = list_business_loans()
active_loans = [loan for loan in loans if loan["status"] == "ACTIVE"]

with st.container(horizontal=True):
    total_outstanding = sum((loan["outstanding_principal"] for loan in loans), 0)
    st.metric("Outstanding debt", format_whole_kwacha(total_outstanding), border=True)
    st.metric("Active loans", str(len(active_loans)), border=True)

mode = st.segmented_control(
    "Loan action",
    ["Record Repayment", "Add Loan", "History"],
    default="Record Repayment",
    key="loan_action",
)

today = today_lusaka()

if mode == "Add Loan":
    with st.form("add_business_loan_form", clear_on_submit=True):
        loan_name = st.text_input("Loan name", placeholder="e.g. Carecoop loan")
        lender = st.text_input("Lender/company/association", placeholder="e.g. Carecoop")
        original_amount = st.number_input("Original principal (K)", min_value=0.0, value=0.0, step=500.0)
        start_date = st.date_input("Start date", value=today, format="DD/MM/YYYY")
        known_repayment = st.number_input(
            "Known repayment amount (K)",
            min_value=0.0,
            value=0.0,
            step=100.0,
        )
        term_months = st.text_input("Term in months", placeholder="Optional")
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save loan", icon=":material/save:", type="primary")
    if submitted:
        try:
            add_business_loan(
                loan_name,
                lender,
                original_amount,
                start_date,
                None if known_repayment == 0 else known_repayment,
                term_months,
                notes,
            )
            st.cache_data.clear()
            st.success("Loan saved.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save loan: {exc}", icon=":material/error:")

elif mode == "Record Repayment":
    loan_options = {"Unidentified loan": None}
    loan_options.update(
        {
            f"{loan['loan_name']} | {loan['lender']} | {format_whole_kwacha(loan['outstanding_principal'])} left": loan[
                "id"
            ]
            for loan in loans
            if loan["status"] == "ACTIVE"
        }
    )
    with st.form("loan_repayment_form", clear_on_submit=True):
        selected_loan = st.selectbox("Loan", list(loan_options))
        payment_source = st.segmented_control(
            "Payment source",
            ["Business funds", "Owner personal funds"],
            default="Business funds",
        )
        repayment_date = st.date_input("Repayment date", value=today, format="DD/MM/YYYY")
        principal = st.number_input("Principal paid (K)", min_value=0.0, value=0.0, step=100.0)
        fees = st.number_input("Interest/fees (K)", min_value=0.0, value=0.0, step=50.0)
        paid_to = st.text_input("Paid to", placeholder="Lender or association")
        reference = st.text_input("Reference", placeholder="Optional")
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Save repayment", icon=":material/payments:", type="primary")
    if submitted:
        try:
            record_loan_repayment(
                repayment_date,
                principal,
                "BUSINESS_ACCOUNT" if payment_source == "Business funds" else "OWNER_PERSONAL",
                loan_id=loan_options[selected_loan],
                paid_to=paid_to,
                interest_or_fees=fees,
                reference=reference,
                notes=notes,
            )
            st.cache_data.clear()
            st.success("Repayment recorded.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not record repayment: {exc}", icon=":material/error:")

if loans:
    st.subheader("Loan list")
    for loan in loans:
        with st.container(border=True):
            st.markdown(f"**{loan['loan_name']}**")
            st.caption(
                f"{loan['lender']} | {loan['status']} | Original {format_whole_kwacha(loan['original_amount'])} | "
                f"Outstanding {format_whole_kwacha(loan['outstanding_principal'])}"
            )
            if loan["default_monthly_repayment"]:
                st.caption(f"Known repayment: {format_whole_kwacha(loan['default_monthly_repayment'])}")
            if loan["notes"]:
                st.write(loan["notes"])
else:
    empty_state("No loans recorded", "Add known business loans when the details are available.", ":material/credit_card:")

repayments = list_loan_repayments()
if repayments:
    st.subheader("Repayment history")
    for repayment in repayments:
        lender = repayment["lender"] or "Unidentified lender"
        source = "Owner personal" if repayment["payment_source"] == "OWNER_PERSONAL" else "Business funds"
        with st.container(border=True):
            st.caption(
                f"{format_date(repayment['repayment_date'])} | {lender} | "
                f"{format_whole_kwacha(repayment['amount'])} | {source}"
            )
            with st.expander("Correction"):
                with st.form(f"cancel_loan_repayment_{repayment['id']}", clear_on_submit=True):
                    reason = st.text_input("Correction reason", key=f"loan_repayment_reason_{repayment['id']}")
                    submitted = st.form_submit_button("Reverse repayment", icon=":material/undo:")
                if submitted:
                    try:
                        cancel_loan_repayment(repayment["id"], reason)
                        st.cache_data.clear()
                        st.success("Repayment reversed.", icon=":material/check_circle:")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not reverse repayment: {exc}", icon=":material/error:")
