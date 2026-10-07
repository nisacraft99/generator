"""Section 1: generate test cases for a user story typed into the page."""

from __future__ import annotations

import streamlit as st

from .. import config
from ..evaluation import evaluate_test_cases
from ..generation import clean_open_questions, generate_test_cases
from ..pdf_report import build_pdf
from ..resources import Resources
from .common import section_label
from .evaluation_view import render_evaluation


def render(resources: Resources) -> None:
    state = st.session_state
    st.markdown('<div class="mock-title">User Story → Testcase Generator</div>', unsafe_allow_html=True)

    section_label("User Story ID (optional; required for evaluation, e.g. US-4)")
    story_id = st.text_input(
        "User Story ID", key="us_id_input", label_visibility="collapsed", placeholder="US-4 (optional)"
    )

    section_label("User Story")
    st.markdown('<div class="field-single singleline">', unsafe_allow_html=True)
    story = st.text_area(
        "User Story",
        key="us_one",
        label_visibility="hidden",
        placeholder="As a <role>, I want ..., so that ...",
        height=200,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    section_label("Acceptance Criteria (one criterion per line)")
    st.markdown('<div class="field-multi">', unsafe_allow_html=True)
    ac_blob = st.text_area(
        "Acceptance Criteria",
        key="ac_lines",
        label_visibility="hidden",
        placeholder="• Criterion 1\n• Criterion 2\n• Criterion 3",
        height=400,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(f"UI context loaded nodes: {len(resources.ui_context.nodes)}")
    st.caption(f"Navigation targets loaded: {len(resources.navigation_targets)}")

    st.markdown('<div class="export-wrap">', unsafe_allow_html=True)
    has_input = bool(story.strip() and ac_blob.strip())
    without_column, with_column, evaluate_column = st.columns(3)
    with without_column:
        clicked_without = st.button("Export without UI context", disabled=not has_input)
    with with_column:
        clicked_with = st.button("Export with UI context", disabled=not has_input)
    with evaluate_column:
        clicked_evaluate = st.button(
            "Evaluate current output", disabled=not (bool(state.last_cases) and story_id.strip())
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if clicked_without or clicked_with:
        with st.spinner("Generating test cases and building PDF..."):
            generation = generate_test_cases(
                resources.client, story, ac_blob, resources.ui_context.raw if clicked_with else None
            )
            state.last_pdf = build_pdf(
                story, ac_blob, generation.cases, generation.open_questions, story_id=story_id.strip()
            )
            state.last_open_questions = generation.open_questions
            state.last_cases_count = len(generation.cases)
            state.last_variant = config.variant_name(clicked_with)
            state.last_cases = generation.cases
            state.last_evaluation = None
        # Rebuild the page so that the buttons above reflect the new output.
        st.rerun()

    if clicked_evaluate and state.last_cases:
        state.last_evaluation = evaluate_test_cases(
            resources,
            story_id.strip(),
            story,
            ac_blob,
            state.last_cases,
            use_ui_context=state.last_variant == config.VARIANT_WITH_UI,
        )
        state.last_pdf = build_pdf(
            story,
            ac_blob,
            state.last_cases,
            state.last_open_questions,
            evaluation=state.last_evaluation,
            story_id=story_id.strip(),
        )

    if state.last_variant:
        st.info(f"Generated with: {state.last_variant}")
    if state.last_open_questions:
        st.warning("Notes / Open Questions:\n- " + "\n- ".join(clean_open_questions(state.last_open_questions)))
    if state.last_evaluation:
        render_evaluation(resources.ui_context, state.last_evaluation, "Automated Evaluation")
    if state.last_pdf:
        st.success(f"PDF ready (test cases: {state.last_cases_count})")
        st.download_button(
            "Download PDF",
            data=state.last_pdf,
            file_name=f"test_design_{story_id}_{state.last_variant or 'result'}.pdf",
            mime="application/pdf",
        )
