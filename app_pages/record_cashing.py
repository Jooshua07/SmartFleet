import streamlit as st

from components.cards import empty_state
from services.bus_service import get_buses_overview
from utils.dates import today_lusaka


st.subheader("Record Cashing")

buses = get_buses_overview(today_lusaka(), status="ACTIVE")
if not buses:
    empty_state(
        "No active buses",
        "Register an active bus and driver assignment before recording cashing.",
        ":material/directions_bus:",
    )
else:
    st.warning(
        "The cashing write workflow is not enabled yet. It must map this simple form to remittance collections, remittances and ledger entries in one transaction.",
        icon=":material/warning:",
    )
    with st.form("record_cashing_form"):
        bus_labels = {f"{bus['registration_number']} - {bus['route_name']}": bus for bus in buses}
        selected = st.selectbox("Bus", list(bus_labels))
        st.info(f"Driver: {bus_labels[selected]['driver_name'] or 'No assigned driver'}", icon=":material/person:")
        st.number_input("Amount (K)", min_value=0.0, step=10.0)
        st.date_input("Date", value=today_lusaka())
        st.text_area("Notes", height=120)
        st.form_submit_button("Record Cashing", type="primary", disabled=True)

