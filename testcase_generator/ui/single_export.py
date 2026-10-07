"""Section 2: generate test cases for one user story from the user story file."""

from __future__ import annotations

import streamlit as st

from .. import config
from ..evaluation import evaluate_test_cases
from ..generation import clean_open_questions, generate_test_cases
from ..pdf_report import build_pdf
from ..resources import Resources, find_user_story, load_user_stories
from .evaluation_view import render_evaluation

_WITH_UI_LABEL = "with UI context"


def render(resources: Resources) -> None:
    state = st.session_state
    st.markdown("---")
    st.subheader("Single User Story Export")
    st.write(
        "Enter a user story number, for example `1` or `US-1`. The app loads the matching entry "
        f"from `{config.USER_STORIES_PATH.name}`. First generate the test cases/PDF, then run the "
        "single evaluation with the separate evaluation button if needed."
    )

    lookup_column, variant_column = st.columns([1, 1])
    with lookup_column:
        lookup = st.text_input("User Story number", key="single_us_lookup", placeholder="e.g. 1 or US-1")
    with variant_column:
        variant_choice = st.radio(
            "Variant", [_WITH_UI_LABEL, "without UI context"], horizontal=False, key="single_variant_choice"
        )

    export_column, evaluate_column = st.columns([1, 1])
    with export_column:
        export_clicked = st.button("Generate single export", disabled=not lookup.strip(), key="single_export_button")
    with evaluate_column:
        evaluate_clicked = st.button(
            "Evaluate single export", disabled=not bool(state.single_cases), key="single_eval_button"
        )

    if export_clicked:
        _generate(resources, lookup, use_ui=variant_choice == _WITH_UI_LABEL)
    if evaluate_clicked:
        _evaluate(resources)

    if state.single_selected_item:
        st.info(
            f"Current single export: {state.single_selected_item['id']} — {state.single_variant or 'not generated'}"
        )
    if state.single_open_questions:
        st.warning(
            "Single export notes / Open Questions:\n- " + "\n- ".join(clean_open_questions(state.single_open_questions))
        )
    if state.single_evaluation:
        render_evaluation(resources.ui_context, state.single_evaluation, "Single Export Evaluation")
    if state.single_export_pdf:
        if state.single_export_info:
            st.info(state.single_export_info)
        st.download_button(
            "Download single export PDF",
            data=state.single_export_pdf,
            file_name=state.single_export_filename,
            mime="application/pdf",
            key="single_export_download",
        )


def _generate(resources: Resources, lookup: str, use_ui: bool) -> None:
    state = st.session_state
    try:
        stories = load_user_stories(config.USER_STORIES_PATH)
        story = find_user_story(stories, lookup)
        if story is None:
            available = ", ".join(entry["id"] for entry in stories[:10])
            st.error(f"No matching user story found for '{lookup}'. Example available IDs: {available}")
            return

        variant = config.variant_name(use_ui)
        with st.spinner(f"Generating single export for {story['id']}..."):
            cases, open_questions = generate_test_cases(
                resources.client, story["story"], story["ac_blob"], resources.ui_context.raw if use_ui else None
            )
            pdf = build_pdf(story["story"], story["ac_blob"], cases, open_questions, story_id=story["id"])

        state.single_selected_item = story
        state.single_variant = variant
        state.single_cases = cases
        state.single_open_questions = open_questions
        state.single_evaluation = None
        state.single_export_pdf = pdf
        state.single_export_filename = f"test_design_{story['id']}_{variant}.pdf"
        state.single_export_info = (
            f"Single export ready for {story['id']} — {variant} (test cases: {len(cases)}). Evaluation not run yet."
        )
        st.success(state.single_export_info)
    except Exception as error:
        state.single_export_pdf = None
        state.single_cases = []
        state.single_open_questions = []
        state.single_evaluation = None
        state.single_selected_item = None
        state.single_variant = None
        st.error(f"Single export failed: {error}")


def _evaluate(resources: Resources) -> None:
    state = st.session_state
    story = state.single_selected_item
    if not story:
        st.warning("Generate a single export first, then run the single evaluation.")
        return
    try:
        with st.spinner(f"Evaluating single export for {story['id']}..."):
            evaluation = evaluate_test_cases(
                resources,
                story["id"],
                story["story"],
                story["ac_blob"],
                state.single_cases,
                use_ui_context=state.single_variant == config.VARIANT_WITH_UI,
            )
            pdf = build_pdf(
                story["story"],
                story["ac_blob"],
                state.single_cases,
                state.single_open_questions,
                evaluation=evaluation,
                story_id=story["id"],
            )
        state.single_evaluation = evaluation
        state.single_export_pdf = pdf
        state.single_export_info = (
            f"Single evaluation ready for {story['id']} — {state.single_variant} "
            f"(test cases: {len(state.single_cases)})"
        )
        st.success(state.single_export_info)
    except Exception as error:
        st.error(f"Single evaluation failed: {error}")
