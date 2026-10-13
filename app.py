import streamlit as st

from components.layout import render_app_header, render_bottom_navigation


st.set_page_config(
    page_title="SmartFleet",
    page_icon=":material/directions_bus:",
    layout="centered",
)


PAGES = [
    st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("app_pages/buses.py", title="Buses", icon=":material/directions_bus:"),
    st.Page("app_pages/finance.py", title="Finance", icon=":material/bar_chart:"),
    st.Page("app_pages/more.py", title="More", icon=":material/apps:"),
    st.Page(
        "app_pages/record_cashing.py",
        title="Record Cashing",
        icon=":material/payments:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/record_expense.py",
        title="Record Expense",
        icon=":material/receipt_long:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/add_bus.py",
        title="Add Bus",
        icon=":material/add_circle:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/reminders.py",
        title="Reminders",
        icon=":material/notifications:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/backups.py",
        title="Backups",
        icon=":material/backup:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/accounts.py",
        title="Bus Accounts",
        icon=":material/account_balance:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/business_presets.py",
        title="Business Presets",
        icon=":material/tune:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/reports.py",
        title="Reports",
        icon=":material/download:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/driver_money.py",
        title="Driver Money",
        icon=":material/id_card:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/loans.py",
        title="Loans",
        icon=":material/credit_card:",
        visibility="hidden",
    ),
    st.Page(
        "app_pages/owner_money.py",
        title="Owner Money",
        icon=":material/account_balance_wallet:",
        visibility="hidden",
    ),
]


current_page = st.navigation(PAGES, position="hidden")
render_app_header(current_page.title, has_fixed_controls=current_page.title in {"Buses", "Finance"})
current_page.run()
render_bottom_navigation(current_page.title)
