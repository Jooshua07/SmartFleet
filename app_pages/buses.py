import streamlit as st

from components.cards import empty_state, status_badge
from components.layout import fixed_page_controls
from services.bus_service import get_bus_details, get_buses_overview, set_bus_status, update_bus
from services.driver_service import create_driver, get_driver, get_drivers_overview, update_driver
from services.route_service import add_route, get_all_routes
from services.maintenance_service import get_servicing_schedules, set_servicing_schedule, servicing_warning
from utils.dates import today_lusaka
from utils.formatting import bus_status_label, format_date


@st.cache_data(ttl=15, max_entries=64, show_spinner=False)
def _load_buses(on_date, search, status):
    return get_buses_overview(on_date, search=search, status=status)


@st.cache_data(ttl=15, max_entries=16, show_spinner=False)
def _load_routes():
    return get_all_routes()


@st.cache_data(ttl=15, max_entries=16, show_spinner=False)
def _load_drivers():
    return get_drivers_overview()


def _route_options(routes: list[dict]) -> dict[str, int]:
    return {route["name"]: route["id"] for route in routes if route["active"]}


def _render_edit_bus(bus_id: int) -> None:
    details = get_bus_details(bus_id)
    bus = details["bus"]
    route_options = _route_options(_load_routes())
    route_labels = list(route_options)
    route_index = next(
        (index for index, label in enumerate(route_labels) if route_options[label] == bus["route_id"]),
        0,
    )

    st.subheader("Edit bus")
    schedule = next((row for row in get_servicing_schedules() if row['bus_id']==bus_id), {})
    with st.form(f"edit_bus_form_{bus_id}"):
        registration_number = st.text_input("Registration number", value=bus["registration_number"])
        route_label = st.selectbox("Route", route_labels, index=route_index)
        route_effective_date = st.date_input(
            "Route effective date",
            value=today_lusaka(),
            format="DD/MM/YYYY",
        )
        model = st.text_input("Model", value=bus["model"] or "")
        seating_capacity = st.text_input(
            "Seating capacity",
            value="" if bus["seating_capacity"] is None else str(bus["seating_capacity"]),
        )
        chassis_number = st.text_input("Chassis number", value=bus["chassis_number"] or "")
        date_acquired = st.date_input(
            "Date acquired",
            value=bus["date_acquired"] or today_lusaka(),
            format="DD/MM/YYYY",
        )
        notes = st.text_area("Notes", value=bus["notes"] or "", height=80)
        next_servicing = st.date_input('Next Servicing Date', value=schedule.get('next_due_date'), format='DD/MM/YYYY')
        frequency = st.number_input('Servicing frequency (days)', min_value=1, value=schedule.get('interval_days') or 35, step=1)
        submitted = st.form_submit_button("Save bus", icon=":material/save:", type="primary")

    if submitted:
        try:
            update_bus(
                bus_id=bus_id,
                registration_number=registration_number,
                route_id=route_options[route_label],
                route_effective_date=route_effective_date,
                model=model,
                seating_capacity=seating_capacity,
                chassis_number=chassis_number,
                date_acquired=date_acquired,
                notes=notes,
            )
            if next_servicing and (next_servicing != schedule.get('next_due_date') or frequency != schedule.get('interval_days')):
                set_servicing_schedule(bus_id,next_servicing,frequency)
            st.cache_data.clear()
            st.session_state.pop("edit_bus_id", None)
            st.success("Bus updated.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not update bus: {exc}", icon=":material/error:")

    with st.container(border=True):
        st.markdown("**Status history**")
        for item in details["status_history"][:5]:
            st.caption(
                f"{bus_status_label(item['status'])} | "
                f"{format_date(item['effective_from'])} to {format_date(item['effective_to'])}"
            )
            if item["reason"]:
                st.caption(item["reason"])

    if st.button("Cancel edit", icon=":material/close:", key=f"cancel_edit_bus_{bus_id}"):
        st.session_state.pop("edit_bus_id", None)
        st.rerun()


def _render_status_change(bus_id: int, status: str) -> None:
    action_label = "Deactivate bus" if status == "INACTIVE" else "Reactivate bus"
    st.subheader(action_label)
    with st.form(f"status_change_form_{bus_id}_{status}"):
        effective_date = st.date_input("Effective date", value=today_lusaka(), format="DD/MM/YYYY")
        reason = st.text_area("Reason", height=80)
        submitted = st.form_submit_button(action_label, icon=":material/save:", type="primary")

    if submitted:
        try:
            set_bus_status(bus_id, status, effective_date, reason)
            st.cache_data.clear()
            st.session_state.pop("status_bus_id", None)
            st.session_state.pop("status_target", None)
            st.success("Bus status updated.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not update bus status: {exc}", icon=":material/error:")

    if st.button("Cancel", icon=":material/close:", key=f"cancel_status_{bus_id}_{status}"):
        st.session_state.pop("status_bus_id", None)
        st.session_state.pop("status_target", None)
        st.rerun()


def _render_edit_driver(driver_id: int) -> None:
    driver = get_driver(driver_id)
    st.subheader("Edit driver")
    with st.form(f"edit_driver_form_{driver_id}"):
        full_name = st.text_input("Driver name", value=driver["full_name"])
        phone = st.text_input("Phone number", value=driver["phone"] or "")
        address = st.text_area("Address", value=driver["address"] or "", height=70)
        next_of_kin_name = st.text_input("Next of kin", value=driver["next_of_kin_name"] or "")
        next_of_kin_phone = st.text_input("Next of kin phone", value=driver["next_of_kin_phone"] or "")
        notes = st.text_area("Notes", value=driver["notes"] or "", height=80)
        submitted = st.form_submit_button("Save driver", icon=":material/save:", type="primary")

    if submitted:
        try:
            update_driver(
                driver_id=driver_id,
                full_name=full_name,
                phone=phone,
                address=address,
                next_of_kin_name=next_of_kin_name,
                next_of_kin_phone=next_of_kin_phone,
                notes=notes,
            )
            st.cache_data.clear()
            st.session_state.pop("edit_driver_id", None)
            st.success("Driver updated.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not update driver: {exc}", icon=":material/error:")

    if st.button("Cancel edit", icon=":material/close:", key=f"cancel_edit_driver_{driver_id}"):
        st.session_state.pop("edit_driver_id", None)
        st.rerun()


with fixed_page_controls():
    selected_section = st.segmented_control(
        "Fleet section",
        ["Buses", "Routes", "Drivers"],
        default="Buses",
        key="fleet_section",
        label_visibility="collapsed",
    )

if selected_section == "Buses":
    edit_bus_id = st.session_state.get("edit_bus_id")
    status_bus_id = st.session_state.get("status_bus_id")
    if edit_bus_id:
        _render_edit_bus(edit_bus_id)
        st.stop()
    if status_bus_id:
        _render_status_change(status_bus_id, st.session_state["status_target"])
        st.stop()

    search = st.text_input(
        "Search buses",
        placeholder="Search by registration, driver or route",
        type="search",
        key="bus_search",
    )
    status_filter = st.pills(
        "Status filter",
        ["All", "Active", "Deactivated"],
        default="All",
        key="bus_status_filter",
    )

    db_status = {"Active": "ACTIVE", "Deactivated": "INACTIVE"}.get(status_filter)
    buses = _load_buses(today_lusaka(), search, db_status)
    schedules = {row['bus_id']:row for row in get_servicing_schedules()}

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
                schedule = schedules.get(bus['id'], {})
                due = schedule.get('next_due_date')
                if due:
                    message = f"Servicing: {format_date(due)} | {servicing_warning(due,today_lusaka())}"
                    level = servicing_warning(due,today_lusaka())
                    if level in ('Urgent','Overdue'):
                        st.error(message)
                    elif level == 'Warning':
                        st.warning(message)
                    else:
                        st.caption(message)
                if st.button('Record Servicing', icon=':material/build:', key=f"service_bus_{bus['id']}"):
                    st.session_state.servicing_bus_id = bus['id']
                    st.session_state.pop('edit_servicing_id',None)
                    st.switch_page('app_pages/record_servicing.py')
                if bus["next_document_expiry"]:
                    st.caption(f"Next document expiry: {format_date(bus['next_document_expiry'])}")
                with st.container(horizontal=True):
                    if st.button("Edit", icon=":material/edit:", key=f"edit_bus_{bus['id']}"):
                        st.session_state.edit_bus_id = bus["id"]
                        st.rerun()
                    target_status = "INACTIVE" if bus["status"] == "ACTIVE" else "ACTIVE"
                    action_label = "Deactivate" if target_status == "INACTIVE" else "Reactivate"
                    if st.button(action_label, icon=":material/power_settings_new:", key=f"status_bus_{bus['id']}"):
                        st.session_state.status_bus_id = bus["id"]
                        st.session_state.status_target = target_status
                        st.rerun()
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
    routes = _load_routes()
    if routes:
        for route in routes:
            with st.container(border=True):
                st.markdown(f"**{route['name']}**")
                st.caption(route["description"] or "No description")
                status_badge("Active" if route["active"] else "Inactive", "ACTIVE" if route["active"] else "INACTIVE")
    else:
        empty_state("No routes", "Add a route before registering buses.", ":material/route:")

    with st.expander("Add route", expanded=False):
        with st.form("add_route_form"):
            route_name = st.text_input("Route name")
            route_description = st.text_area("Description", height=80)
            submitted = st.form_submit_button("Add route", icon=":material/add:")
        if submitted:
            try:
                add_route(route_name, route_description or None)
                st.cache_data.clear()
                st.success("Route added.", icon=":material/check_circle:")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add route: {exc}", icon=":material/error:")

else:
    st.subheader("Drivers")
    edit_driver_id = st.session_state.get("edit_driver_id")
    if edit_driver_id:
        _render_edit_driver(edit_driver_id)
        st.stop()

    if st.session_state.pop("driver_saved", False):
        st.success("Driver added.", icon=":material/check_circle:")

    drivers = _load_drivers()
    if drivers:
        for driver in drivers:
            with st.container(border=True):
                st.markdown(f"**{driver['full_name']}**")
                st.caption(driver["phone"] or "No phone recorded")
                st.caption(driver["assigned_bus"] or "No active bus assignment")
                if st.button("Edit", icon=":material/edit:", key=f"edit_driver_{driver['id']}"):
                    st.session_state.edit_driver_id = driver["id"]
                    st.rerun()
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
                st.cache_data.clear()
                st.session_state.driver_saved = True
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add driver: {exc}", icon=":material/error:")
