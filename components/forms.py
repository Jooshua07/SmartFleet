import streamlit as st


def show_success_once(key: str, message: str) -> None:
    if st.session_state.pop(key, False):
        st.success(message, icon=":material/check_circle:")


def set_success(key: str) -> None:
    st.session_state[key] = True

