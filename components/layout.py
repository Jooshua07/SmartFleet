from dataclasses import dataclass
import os

import streamlit as st
from dotenv import load_dotenv


load_dotenv()


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


def inject_app_shell_styles(has_fixed_controls: bool) -> None:
    content_top = "8.6rem" if has_fixed_controls else "4.8rem"
    st.html(
        f"""
        <style>
        header[data-testid="stHeader"] {{
            background: transparent;
            height: 0;
        }}

        [data-testid="stAppViewContainer"] > .main .block-container {{
            max-width: 480px;
            padding: {content_top} 0.85rem 6.25rem;
        }}

        .st-key-smartfleet_app_bar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: #ffffff;
            border-bottom: 1px solid #dbe4f0;
            box-shadow: 0 8px 22px rgba(8, 19, 49, 0.08);
        }}

        .st-key-smartfleet_app_bar > div {{
            max-width: 480px;
            min-height: 3.75rem;
            margin: 0 auto;
            padding: 0.55rem 0.85rem 0.45rem;
        }}

        .st-key-smartfleet_app_bar h3 {{
            margin: 0;
            line-height: 1.05;
            font-size: 1.08rem;
            letter-spacing: 0;
        }}

        .st-key-smartfleet_app_bar [data-testid="stCaptionContainer"] {{
            margin-top: -0.15rem;
            color: #4a5875;
            font-size: 0.78rem;
        }}

        .st-key-smartfleet_page_controls {{
            position: fixed;
            top: 3.72rem;
            left: 0;
            right: 0;
            z-index: 999;
            background: #ffffff;
            border-bottom: 1px solid #dbe4f0;
            box-shadow: 0 8px 16px rgba(8, 19, 49, 0.05);
        }}

        .st-key-smartfleet_page_controls > div {{
            max-width: 480px;
            margin: 0 auto;
            padding: 0.45rem 0.85rem 0.55rem;
        }}

        .st-key-smartfleet_page_controls [data-testid="stCaptionContainer"] {{
            margin-top: -0.3rem;
            color: #4a5875;
            font-size: 0.76rem;
        }}

        .st-key-smartfleet_page_controls [data-testid="stWidgetLabel"] {{
            margin-bottom: 0.2rem;
        }}

        .st-key-smartfleet_page_controls .stSegmentedControl {{
            margin-bottom: 0;
        }}

        div[data-testid="stBottom"] {{
            border-top: 1px solid #dbe4f0;
            box-shadow: 0 -8px 18px rgba(8, 19, 49, 0.06);
        }}

        @media (min-width: 720px) {{
            [data-testid="stAppViewContainer"] > .main .block-container {{
                padding-left: 0;
                padding-right: 0;
            }}
        }}
        </style>
        """
    )


def render_app_header(page_title: str, has_fixed_controls: bool = False) -> None:
    inject_app_shell_styles(has_fixed_controls)
    caption = page_title
    if os.getenv("DB_NAME") != "smartfleet":
        caption = f"{page_title} | Demo database"
    with st.container(key="smartfleet_app_bar", horizontal=True, vertical_alignment="center"):
        st.markdown("### SmartFleet")
        st.caption(caption)


def fixed_page_controls():
    return st.container(key="smartfleet_page_controls")


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
