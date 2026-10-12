import streamlit as st

from services.account_service import get_accounts_for_management, update_opening_balance
from utils.formatting import format_whole_kwacha


st.subheader("Accounts")

st.warning(
    "Opening balances should be set before daily records begin. Changing them later changes calculated balances.",
    icon=":material/warning:",
)

if st.session_state.pop("account_saved", False):
    st.success("Account balance updated.", icon=":material/check_circle:")

accounts = get_accounts_for_management()
if not accounts:
    st.caption("No accounts found.")
else:
    for account in accounts:
        with st.container(border=True):
            st.markdown(f"**{account['name']}**")
            st.caption(account["account_type"])
            st.metric("Calculated balance", format_whole_kwacha(account["calculated_balance"]))
            if account["transaction_count"]:
                st.caption(f"{account['transaction_count']} ledger entries already use this account.")

            with st.form(f"account_balance_form_{account['id']}"):
                opening_balance = st.number_input(
                    "Opening balance (K)",
                    min_value=0.0,
                    value=float(account["opening_balance"]),
                    step=50.0,
                    key=f"opening_balance_{account['id']}",
                )
                submitted = st.form_submit_button("Save opening balance", icon=":material/save:")

            if submitted:
                try:
                    update_opening_balance(account["id"], opening_balance)
                    st.session_state.account_saved = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update account: {exc}", icon=":material/error:")
