import streamlit as st

from components.layout import quick_action
from services.validation_service import get_data_validation_warnings


st.subheader("Quick actions")

quick_action("Record Cashing", "app_pages/record_cashing.py", ":material/payments:")
quick_action("Record Expense", "app_pages/record_expense.py", ":material/receipt_long:")
quick_action("Add Bus", "app_pages/add_bus.py", ":material/add_circle:")
quick_action("Drivers", "app_pages/buses.py", ":material/person:")
quick_action("Reminders", "app_pages/reminders.py", ":material/notifications:")
quick_action("Reports", "app_pages/reports.py", ":material/download:")
quick_action("Backups", "app_pages/backups.py", ":material/backup:")

st.subheader("Management")
quick_action("Accounts", "app_pages/accounts.py", ":material/account_balance:")

st.subheader("Checks")
warnings = get_data_validation_warnings()
if warnings:
    for warning in warnings:
        st.warning(warning, icon=":material/warning:")
else:
    st.success("No setup warnings right now.", icon=":material/check_circle:")
