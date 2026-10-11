from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class NavItem:
    title: str
    path: str
    icon: str


BOTTOM_NAV_ITEMS = (
    NavItem("Home", "app_pages/home.py", ":material/home:"),
    NavItem("Buses", "app_pages/buses.py", ":material/directions_bus:"),
    NavItem("Finance", "app_pages/finance.py", ":material/bar_chart:"),
    NavItem("More", "app_pages/more.py", ":material/apps:"),
)


def render_app_header(page_title: str) -> None:
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("### SmartFleet")
        st.caption(page_title)


def render_bottom_navigation(current_title: str) -> None:
    with st.bottom:
        with st.container(horizontal=True, horizontal_alignment="distribute", wrap=False):
            for item in BOTTOM_NAV_ITEMS:
                active = current_title == item.title
                if st.button(
                    item.title,
                    key=f"bottom_nav_{item.title}",
                    icon=item.icon,
                    type="primary" if active else "tertiary",
                    width="stretch",
                    disabled=active,
                ):
                    st.switch_page(item.path)


def quick_action(label: str, path: str, icon: str) -> None:
    if st.button(label, icon=icon, width="stretch"):
        st.switch_page(path)

