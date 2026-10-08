"""Page setup shared by all sections: styling, login, session state and progress display."""

from __future__ import annotations

import os

import streamlit as st

from .. import config

_SESSION_DEFAULTS = {
    # Free-text export
    "last_pdf": None,
    "last_open_questions": list,
    "last_cases_count": 0,
    "last_variant": None,
    "last_cases": list,
    "last_evaluation": None,
    # Single export from the user story file
    "single_export_pdf": None,
    "single_export_filename": "single_test_design.pdf",
    "single_export_info": "",
    "single_cases": list,
    "single_open_questions": list,
    "single_evaluation": None,
    "single_selected_item": None,
    "single_variant": None,
}


def apply_styles() -> None:
    css = config.STYLESHEET_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>\n{css}</style>", unsafe_allow_html=True)


def init_session_state() -> None:
    for key, default in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default() if callable(default) else default


def _configured_password() -> str:
    fallback = os.getenv("APP_PASSWORD", "")
    try:
        return st.secrets.get("APP_PASSWORD", fallback)
    except FileNotFoundError:
        # No secrets.toml, e.g. on a local machine.
        return fallback


def require_login() -> None:
    """Show the password prompt and stop the page until the password is correct.

    The password comes from the Streamlit secret or environment variable APP_PASSWORD.
    """
    password = _configured_password()
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    def try_login() -> None:
        if password and st.session_state.get("pw_input", "") == password:
            st.session_state.auth_ok = True
            st.session_state.pop("pw_error", None)
        else:
            st.session_state.pw_error = "Wrong password."

    if st.session_state.auth_ok:
        return

    st.markdown(
        """
        <div class="login-card">
          <div class="login-title">User Story to Testcase Generator</div>
          <p class="login-note">Private application. Enter the password to continue.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.text_input("Password", type="password", key="pw_input")
    st.button("Sign in", on_click=try_login)
    if st.session_state.get("pw_error"):
        st.error(st.session_state["pw_error"])
    st.stop()


def section_label(text: str) -> None:
    st.markdown(f'<div class="mock-label">{text}</div>', unsafe_allow_html=True)
