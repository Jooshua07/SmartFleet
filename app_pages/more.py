import streamlit as st

from components.layout import quick_action


st.subheader("Quick actions")

quick_action("Record Cashing", "app_pages/record_cashing.py", ":material/payments:")
quick_action("Record Expense", "app_pages/record_expense.py", ":material/receipt_long:")
quick_action("Add Bus", "app_pages/add_bus.py", ":material/add_circle:")
quick_action("Drivers", "app_pages/buses.py", ":material/person:")
quick_action("Reminders", "app_pages/reminders.py", ":material/notifications:")

st.subheader("Management")
st.caption("Additional management screens will be added as the business modules are implemented.")

