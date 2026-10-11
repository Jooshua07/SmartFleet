from collections.abc import Iterable

import streamlit as st


def metric_card(label: str, value: str, caption: str | None = None, icon: str | None = None) -> None:
    st.metric(label, value, border=True, icon=icon)
    if caption:
        st.caption(caption)


def empty_state(title: str, body: str, icon: str = ":material/info:") -> None:
    with st.container(border=True):
        st.info(f"{title}\n\n{body}", icon=icon)


def status_badge(label: str, status: str) -> None:
    color = {
        "ACTIVE": "green",
        "INACTIVE": "red",
        "PENDING": "orange",
        "COMPLETED": "green",
        "DISMISSED": "gray",
    }.get(status, "blue")
    st.badge(label, color=color)


def simple_list(items: Iterable[str], empty_message: str) -> None:
    rendered = False
    for item in items:
        rendered = True
        st.markdown(f"- {item}")
    if not rendered:
        st.caption(empty_message)

