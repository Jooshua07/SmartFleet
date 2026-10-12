import streamlit as st

from services.bus_service import create_bus
from services.driver_service import get_available_driver_employments
from services.route_service import get_active_routes
from utils.dates import today_lusaka
from utils.validation import parse_optional_positive_int


DOCUMENT_FIELDS = (
    ("INSURANCE", "Insurance"),
    ("ROAD_TAX", "Road tax"),
    ("FITNESS", "Fitness or roadworthiness"),
)


st.session_state.setdefault("add_bus_step", 1)
st.session_state.setdefault("add_bus_draft", {})

step = st.session_state.add_bus_step
draft = st.session_state.add_bus_draft

st.progress(step / 3)
st.caption(f"Step {step} of 3")

if step == 1:
    with st.form("add_bus_basic"):
        st.subheader("Bus details")
        registration_number = st.text_input(
            "Registration number",
            value=draft.get("registration_number", ""),
            placeholder="e.g. ABC 1234",
        )
        model = st.text_input(
            "Model",
            value=draft.get("model", ""),
            placeholder="e.g. Toyota Coaster",
        )
        seating_capacity = st.text_input(
            "Seating capacity",
            value=str(draft.get("seating_capacity") or ""),
            placeholder="e.g. 70",
        )
        chassis_number = st.text_input(
            "Chassis number",
            value=draft.get("chassis_number", ""),
            placeholder="Optional",
        )
        date_acquired = st.date_input(
            "Acquisition date",
            value=draft.get("date_acquired", today_lusaka()),
            format="DD/MM/YYYY",
        )
        next_clicked = st.form_submit_button("Next", icon=":material/arrow_forward:", type="primary")

    if next_clicked:
        try:
            seats = parse_optional_positive_int(seating_capacity, "Seating capacity")
            if not registration_number.strip():
                st.error("Registration number is required.", icon=":material/error:")
            else:
                draft["registration_number"] = registration_number.strip()
                draft["model"] = model.strip()
                draft["seating_capacity"] = seats
                draft["chassis_number"] = chassis_number.strip()
                draft["date_acquired"] = date_acquired
                st.session_state.add_bus_step = 2
                st.rerun()
        except ValueError as exc:
            st.error(str(exc), icon=":material/error:")

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
            st.subheader("Route and driver")
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
            draft["notes"] = notes.strip()
            st.session_state.add_bus_step = 3
            st.rerun()

else:
    st.subheader("Documents and review")
    st.caption("Record expiry dates now if you know them. You can leave them blank.")

    existing_documents = {
        document.get("document_type"): document
        for document in draft.get("document_records", [])
    }

    with st.form("add_bus_documents"):
        document_records = []
        for document_type, label in DOCUMENT_FIELDS:
            existing = existing_documents.get(document_type, {})
            with st.container(border=True):
                st.markdown(f"**{label}**")
                document_number = st.text_input(
                    f"{label} number/reference",
                    value=existing.get("document_number") or "",
                    key=f"add_bus_{document_type}_number",
                )
                expiry_date = st.date_input(
                    f"{label} expiry date",
                    value=existing.get("expiry_date"),
                    format="DD/MM/YYYY",
                    key=f"add_bus_{document_type}_expiry",
                )
                notes = st.text_input(
                    f"{label} notes",
                    value=existing.get("notes") or "",
                    placeholder="Optional",
                    key=f"add_bus_{document_type}_notes",
                )
                document_records.append(
                    {
                        "document_type": document_type,
                        "document_number": document_number.strip(),
                        "issue_date": None,
                        "expiry_date": expiry_date,
                        "notes": notes.strip(),
                    }
                )

        st.markdown("**Review**")
        st.markdown(f"**Registration number:** {draft.get('registration_number')}")
        st.markdown(f"**Model:** {draft.get('model') or 'Not set'}")
        st.markdown(f"**Seating capacity:** {draft.get('seating_capacity') or 'Not set'}")
        st.markdown(f"**Route:** {draft.get('route_name')}")
        st.markdown(f"**Driver:** {draft.get('driver_name', 'No initial driver')}")
        st.markdown(f"**Initial status:** {draft.get('status')}")
        st.markdown(f"**Acquisition date:** {draft.get('date_acquired')}")
        st.markdown(f"**Notes:** {draft.get('notes') or 'None'}")

        with st.container(horizontal=True):
            back = st.form_submit_button("Back", icon=":material/arrow_back:")
            submit = st.form_submit_button("Submit/Add Bus", icon=":material/add_circle:", type="primary")

    if back:
        draft["document_records"] = document_records
        st.session_state.add_bus_step = 2
        st.rerun()

    if submit:
        try:
            draft["document_records"] = document_records
            create_bus(
                draft.get("registration_number"),
                draft.get("route_id"),
                status=draft.get("status"),
                date_acquired=draft.get("date_acquired"),
                notes=draft.get("notes"),
                employment_id=draft.get("employment_id"),
                model=draft.get("model"),
                seating_capacity=draft.get("seating_capacity"),
                chassis_number=draft.get("chassis_number"),
                document_records=document_records,
            )
            st.session_state.add_bus_step = 1
            st.session_state.add_bus_draft = {}
            for document_type, _ in DOCUMENT_FIELDS:
                st.session_state.pop(f"add_bus_{document_type}_number", None)
                st.session_state.pop(f"add_bus_{document_type}_expiry", None)
                st.session_state.pop(f"add_bus_{document_type}_notes", None)
            st.success("Bus added.", icon=":material/check_circle:")
        except Exception as exc:
            st.error(f"Could not add bus: {exc}", icon=":material/error:")
