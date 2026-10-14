import streamlit as st


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
