import streamlit as st

from components.cards import empty_state
from services.reminder_service import get_deactivated_buses, get_due_maintenance, get_open_reminders
from utils.dates import today_lusaka
from utils.formatting import format_date


today = today_lusaka()

st.subheader("Upcoming maintenance")
maintenance = get_due_maintenance(today, days=21)
if maintenance:
    for item in maintenance:
        with st.container(border=True):
            st.markdown(f"**{item['registration_number']}**")
            st.caption(f"{item['schedule_name']} due {format_date(item['next_due_date'])}")
else:
    st.caption("No maintenance due in the next 21 days.")

st.subheader("Deactivated buses")
deactivated = get_deactivated_buses()
if deactivated:
    for bus in deactivated:
        with st.container(border=True):
            st.markdown(f"**{bus['registration_number']}**")
            st.caption(f"Last status update: {format_date(bus['updated_at'].date())}")
else:
    st.caption("No deactivated buses.")

st.subheader("Stored reminders")
reminders = get_open_reminders()
if reminders:
    for reminder in reminders:
        with st.container(border=True):
            st.markdown(f"**{reminder['title']}**")
            st.caption(f"{reminder['reminder_type']} due {format_date(reminder['due_date'])}")
            if reminder["description"]:
                st.write(reminder["description"])
else:
    empty_state("No pending reminders", "Stored reminders will appear here.", ":material/notifications:")

