import streamlit as st

from components.cards import empty_state, status_badge
from components.layout import fixed_page_controls
from services.bus_service import get_buses_overview
from services.driver_service import create_driver, get_drivers_overview
from services.route_service import add_route, get_all_routes
from utils.dates import today_lusaka
from utils.formatting import bus_status_label, format_date


with fixed_page_controls():
    selected_section = st.segmented_control(
        "Fleet section",
        ["Buses", "Routes", "Drivers"],
        default="Buses",
        key="fleet_section",
        label_visibility="collapsed",
    )

if selected_section == "Buses":
    search = st.text_input(
        "Search buses",
        placeholder="Search by registration, driver or route",
        type="search",
        key="bus_search",
    )
    status_filter = st.pills(
        "Status filter",
        ["All", "Active", "In Garage", "Deactivated"],
        default="All",
        key="bus_status_filter",
    )

    if status_filter == "In Garage":
        st.warning(
            "In Garage is not a stored bus status yet. It needs an approved maintenance/downtime definition.",
            icon=":material/warning:",
        )
        buses = []
    else:
        db_status = {"Active": "ACTIVE", "Deactivated": "INACTIVE"}.get(status_filter)
        buses = get_buses_overview(today_lusaka(), search=search, status=db_status)

    if buses:
        for bus in buses:
            with st.container(border=True):
                with st.container(horizontal=True, horizontal_alignment="distribute"):
                    st.markdown(f"**{bus['registration_number']}**")
                    status_badge(bus_status_label(bus["status"]), bus["status"])
                driver = bus["driver_name"] or "No assigned driver"
                model = bus["model"] or "Model not set"
                seats = f"{bus['seating_capacity']} seats" if bus["seating_capacity"] else "Seats not set"
                st.caption(f"{driver} | {bus['route_name']}")
                st.caption(f"{model} | {seats}")
                st.caption(f"Acquired: {format_date(bus['date_acquired'])}")
                if bus["next_document_expiry"]:
                    st.caption(f"Next document expiry: {format_date(bus['next_document_expiry'])}")
    else:
        empty_state(
            "No buses to show",
            "Register your first bus to start building the fleet record.",
            ":material/directions_bus:",
        )

    if st.button("Add New Bus", icon=":material/add_circle:", type="primary", width="stretch"):
        st.switch_page("app_pages/add_bus.py")

elif selected_section == "Routes":
    st.subheader("Routes")
    routes = get_all_routes()
    if routes:
        for route in routes:
            with st.container(border=True):
                st.markdown(f"**{route['name']}**")
                st.caption(route["description"] or "No description")
                status_badge("Active" if route["active"] else "Inactive", "ACTIVE" if route["active"] else "INACTIVE")
    else:
        empty_state("No routes", "Add a route before registering buses.", ":material/route:")

    with st.form("add_route_form"):
        st.markdown("**Add route**")
        route_name = st.text_input("Route name")
        route_description = st.text_area("Description", height=80)
        submitted = st.form_submit_button("Add route", icon=":material/add:")
    if submitted:
        try:
            add_route(route_name, route_description or None)
            st.success("Route added.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not add route: {exc}", icon=":material/error:")

else:
    st.subheader("Drivers")
    if st.session_state.pop("driver_saved", False):
        st.success("Driver added.", icon=":material/check_circle:")

    drivers = get_drivers_overview()
    if drivers:
        for driver in drivers:
            with st.container(border=True):
                st.markdown(f"**{driver['full_name']}**")
                st.caption(driver["phone"] or "No phone recorded")
                st.caption(driver["assigned_bus"] or "No active bus assignment")
    else:
        empty_state(
            "No drivers registered",
            "Add drivers here before assigning them to buses.",
            ":material/person:",
        )

    with st.expander("Add driver"):
        with st.form("add_driver_form"):
            full_name = st.text_input("Driver name")
            phone = st.text_input("Phone number")
            start_date = st.date_input("Employment start date", value=today_lusaka(), format="DD/MM/YYYY")
            monthly_salary = st.text_input("Monthly salary", value="2000.00")
            notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Add driver", icon=":material/person_add:", type="primary")

        if submitted:
            try:
                create_driver(
                    full_name=full_name,
                    phone=phone,
                    start_date=start_date,
                    monthly_salary=monthly_salary,
                    notes=notes,
                )
                st.session_state.driver_saved = True
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add driver: {exc}", icon=":material/error:")
