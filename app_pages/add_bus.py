import streamlit as st

from services.bus_service import create_bus
from services.driver_service import get_available_driver_employments
from services.route_service import get_active_routes
from utils.dates import today_lusaka


st.warning(
    "The current database does not store bus model, seating capacity or uploaded documents. "
    "This wizard records only schema-supported bus details until an additive migration is approved.",
    icon=":material/database:",
)

st.session_state.setdefault("add_bus_step", 1)
st.session_state.setdefault("add_bus_draft", {})

step = st.session_state.add_bus_step
draft = st.session_state.add_bus_draft

st.progress(step / 3)
st.caption(f"Step {step} of 3")

if step == 1:
    with st.form("add_bus_basic"):
        st.subheader("Basic information")
        registration_number = st.text_input(
            "Registration number",
            value=draft.get("registration_number", ""),
            placeholder="e.g. ABC 1234",
        )
        date_acquired = st.date_input(
            "Acquisition date",
            value=draft.get("date_acquired", today_lusaka()),
        )
        next_clicked = st.form_submit_button("Next", icon=":material/arrow_forward:", type="primary")

    if next_clicked:
        if not registration_number.strip():
            st.error("Registration number is required.", icon=":material/error:")
        else:
            draft["registration_number"] = registration_number.strip()
            draft["date_acquired"] = date_acquired
            st.session_state.add_bus_step = 2
            st.rerun()

elif step == 2:
    routes = get_active_routes()
    drivers = get_available_driver_employments(draft.get("date_acquired", today_lusaka()))

    if not routes:
        st.error("Add an active route before registering a bus.", icon=":material/error:")
    else:
        route_options = {route["name"]: route["id"] for route in routes}
        driver_options = {"No initial driver": None}
        driver_options.update({driver["full_name"]: driver["employment_id"] for driver in drivers})

        with st.form("add_bus_assignment"):
            st.subheader("Assignment")
            route_name = st.selectbox("Route", list(route_options), index=0)
            driver_name = st.selectbox("Driver", list(driver_options), index=0)
            status_label = st.selectbox("Initial status", ["Active", "Deactivated"], index=0)
            notes = st.text_area("Additional information / notes", value=draft.get("notes", ""), height=120)
            with st.container(horizontal=True):
                back = st.form_submit_button("Back", icon=":material/arrow_back:")
                next_clicked = st.form_submit_button("Next", icon=":material/arrow_forward:", type="primary")

        if back:
            st.session_state.add_bus_step = 1
            st.rerun()
        if next_clicked:
            draft["route_id"] = route_options[route_name]
            draft["route_name"] = route_name
            draft["employment_id"] = driver_options[driver_name]
            draft["driver_name"] = driver_name
            draft["status"] = "ACTIVE" if status_label == "Active" else "INACTIVE"
            draft["notes"] = notes.strip() or None
            st.session_state.add_bus_step = 3
            st.rerun()

else:
    st.subheader("Documents and review")
    st.info(
        "Document uploads are not persisted yet. Add document storage only after the database design is approved.",
        icon=":material/info:",
    )

    with st.container(border=True):
        st.markdown(f"**Registration number:** {draft.get('registration_number')}")
        st.markdown(f"**Route:** {draft.get('route_name')}")
        st.markdown(f"**Driver:** {draft.get('driver_name', 'No initial driver')}")
        st.markdown(f"**Initial status:** {draft.get('status')}")
        st.markdown(f"**Acquisition date:** {draft.get('date_acquired')}")
        st.markdown(f"**Notes:** {draft.get('notes') or 'None'}")

    with st.container(horizontal=True):
        if st.button("Back", icon=":material/arrow_back:"):
            st.session_state.add_bus_step = 2
            st.rerun()
        if st.button("Submit/Add Bus", icon=":material/add_circle:", type="primary"):
            try:
                create_bus(
                    draft.get("registration_number"),
                    draft.get("route_id"),
                    draft.get("status"),
                    draft.get("date_acquired"),
                    draft.get("notes"),
                    draft.get("employment_id"),
                )
                st.session_state.add_bus_step = 1
                st.session_state.add_bus_draft = {}
                st.success("Bus added.", icon=":material/check_circle:")
            except Exception as exc:
                st.error(f"Could not add bus: {exc}", icon=":material/error:")

