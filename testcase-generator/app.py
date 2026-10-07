"""Streamlit entry point of the User Story → Testcase Generator.

Run with:  streamlit run app.py
"""

import streamlit as st

from testcase_generator.resources import load_resources
from testcase_generator.ui import bulk_evaluation, manual_export, single_export
from testcase_generator.ui.common import apply_styles, init_session_state, require_login


def main() -> None:
    st.set_page_config(page_title="User Story → Testcase Generator", page_icon="🧪", layout="wide")
    apply_styles()
    require_login()

    init_session_state()
    resources = load_resources()

    manual_export.render(resources)
    single_export.render(resources)
    bulk_evaluation.render(resources)


main()
