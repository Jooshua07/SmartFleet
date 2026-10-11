import streamlit as st

from components.cards import empty_state


st.subheader("Record Expense")

empty_state(
    "Expense recording is planned next",
    "This form must use the existing expense, allocation and payment-source schema before writes are enabled.",
    ":material/receipt_long:",
)

