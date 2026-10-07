"""Display of the metrics of one evaluated output, with the evidence behind each value."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ..ui_model import UiContext


def _percent(value: Any) -> str:
    return "N/A" if value is None else f"{value}%"


def _status(covered: bool) -> str:
    return "Covered" if covered else "Not covered"


def render_evaluation(ui: UiContext, evaluation: dict[str, Any], header: str = "Automated Evaluation") -> None:
    ac = evaluation.get("ac", {})
    role = evaluation.get("role", {})
    target_node = evaluation.get("target_node", {})
    navigation = evaluation.get("navigation_path", {})

    consistency = evaluation.get("id_text_consistency", {})
    console_naming = evaluation.get("console_naming", {})

    st.subheader(header)
    both_variants = st.columns(3)
    both_variants[0].metric("AC Coverage", _percent(ac.get("overall_pct")))
    both_variants[1].metric("Role Coverage", _percent(role.get("overall_pct")))
    both_variants[2].metric("Console Naming", _percent(console_naming.get("named_pct")))
    with_ui_only = st.columns(3)
    with_ui_only[0].metric("Target Node Coverage", _percent(target_node.get("coverage_pct")))
    with_ui_only[1].metric("Navigation Path Correctness", _percent(navigation.get("correctness_pct")))
    with_ui_only[2].metric("ID-Text Consistency", _percent(consistency.get("consistency_pct")))

    _render_ac_coverage(ac)
    _render_role_coverage(role)
    _render_console_naming(console_naming)
    _render_target_node_coverage(target_node)
    _render_navigation_path(ui, navigation)
    _render_id_text_consistency(consistency)


def _render_ac_coverage(ac: dict[str, Any]) -> None:
    st.write("**AC Coverage**")
    if ac.get("note"):
        st.warning(ac["note"])
        return
    st.write(f"{ac.get('covered_count', 0)}/{ac.get('total_count', 0)} acceptance criteria covered")
    with st.expander("AC Coverage details and reasons"):
        for detail in ac.get("details", []):
            st.write(f"**{detail.get('ac_id', '')} — {_status(bool(detail.get('covered')))}**")
            st.write(detail.get("ac_text", ""))
            st.caption(f"Reason: {detail.get('reason') or 'No reason returned.'}")


def _render_role_coverage(role: dict[str, Any]) -> None:
    st.write("**Role Coverage**")
    required = role.get("required_roles", []) or []
    generated = role.get("generated_roles", []) or []
    missing = role.get("missing_roles", []) or []

    if role.get("overall_pct") is None and not required:
        st.caption("No required user roles were found in this user story or its acceptance criteria.")
        return
    st.write(f"{role.get('covered_count', 0)}/{role.get('total_count', 0)} required roles covered")
    with st.expander("Role Coverage details and reasons"):
        for name in required:
            covered = name in generated
            finding = "An" if covered else "No"
            st.write(f"**{name.title()} — {_status(covered)}**")
            st.caption(
                f"Reason: {finding} explicit role/login reference for '{name}' was found in the generated test cases."
            )
        if missing:
            st.caption(f"Missing roles: {', '.join(missing)}")


def _render_target_node_coverage(target_node: dict[str, Any]) -> None:
    st.write("**Target Node Coverage**")
    if target_node.get("note"):
        st.info(target_node["note"])
        return
    st.write(
        f"{target_node.get('covered_count', 0)}/{target_node.get('total_count', 0)} "
        "required_across_story target nodes reached"
    )
    with st.expander("Target Node Coverage details and reasons"):
        for detail in target_node.get("details", []):
            covered = bool(detail.get("covered"))
            node_id = detail.get("node_id", "")
            if covered:
                reason = (
                    "The expected target node is reached by an explicit ui_node_id or by the immediate "
                    "target of an explicitly activated relationship in ui_context.json."
                )
            else:
                reason = (
                    "The expected target node is neither emitted as a ui_node_id nor reached as the immediate "
                    "target of an explicitly activated relationship in ui_context.json."
                )
            st.write(f"**{node_id} — {detail.get('node_name', node_id)} — {_status(covered)}**")
            st.caption(f"Reason: {reason}")


def _render_navigation_path(ui: UiContext, navigation: dict[str, Any]) -> None:
    def path_text(node_ids: list[str]) -> str:
        return " → ".join(ui.name_of(node_id) for node_id in node_ids) or "—"

    st.write("**Navigation Path Correctness**")
    if navigation.get("note"):
        st.info(navigation["note"])
        return

    skipped = navigation.get("skipped_count") or 0
    st.write(
        f"{navigation.get('correct_count', 0)}/{navigation.get('evaluated_count', 0)} "
        f"evaluable test-case paths correct{f'; {skipped} skipped' if skipped else ''}"
    )
    st.caption(
        "Each test case must contain all required_per_testcase nodes in the correct order. "
        "Additional or repeated known UI nodes are allowed and are not evaluated as direct transitions. "
        "required_across_story is scored separately under Target Node Coverage."
    )
    without_skipping = navigation.get("correctness_pct_without_skipping")
    if without_skipping is not None:
        st.caption(f"Counting the skipped no-access tests as well: {without_skipping}%")
    with st.expander("Navigation Path Correctness details and reasons"):
        for detail in navigation.get("details", []):
            case_id = detail.get("tc_id", "") or "Test case"
            if not detail.get("can_evaluate"):
                st.write(f"**{case_id} — Skipped**")
                st.caption(f"Reason: {detail.get('skip_reason') or 'No evaluable navigation path.'}")
                continue

            is_correct = bool(detail.get("is_correct"))
            missing = detail.get("missing_nodes", []) or []
            unknown = detail.get("invalid_ui_node_ids", []) or []
            if is_correct:
                reason = (
                    "All required_per_testcase nodes occur in the required order. "
                    "Additional or repeated known UI nodes are allowed."
                )
            elif missing:
                reason = f"Required per-testcase nodes are missing: {path_text(missing)}."
            elif unknown:
                reason = f"Unknown ui_node_id value(s) not found in ui_context.json: {', '.join(unknown)}."
            else:
                reason = "The required per-testcase nodes are present but do not occur in the required order."

            st.write(
                f"**{case_id} — {detail.get('selected_target', '') or 'navigation path'} — "
                f"{'Correct' if is_correct else 'Incorrect'}**"
            )
            st.caption(f"Expected: {path_text(detail.get('expected', []) or [])}")
            st.caption(f"Actual: {path_text(detail.get('actual', []) or [])}")
            st.caption(f"Reason: {reason}")


def _render_console_naming(console_naming: dict[str, Any]) -> None:
    st.write("**Console Naming**")
    if not console_naming:
        st.caption("Not available in this saved run.")
        return
    if console_naming.get("note"):
        st.info(console_naming["note"])
        return
    st.write(
        f"{console_naming.get('named_count', 0)}/{console_naming.get('total_count', 0)} test cases name the console "
        f"'{console_naming.get('expected_console')}' in a step"
    )
    st.caption(
        "Only the step text is read, not the ui_node_id values, so this metric is computed the same way "
        "with and without UI context."
    )
    with st.expander("Console Naming details"):
        for detail in console_naming.get("details", []):
            named = ", ".join(detail.get("consoles_named", [])) or "no console"
            st.write(
                f"**{detail.get('tc_id', '') or 'Test case'} — {'Named' if detail.get('named') else 'Not named'}**"
            )
            st.caption(f"Consoles named in the steps: {named}")


def _render_id_text_consistency(consistency: dict[str, Any]) -> None:
    st.write("**ID-Text Consistency**")
    if not consistency:
        st.caption("Not available in this saved run.")
        return
    if consistency.get("note"):
        st.info(consistency["note"])
        return
    st.write(
        f"{consistency.get('consistent_count', 0)}/{consistency.get('total_count', 0)} test cases without a step "
        "whose text contradicts its ui_node_id"
    )
    st.caption(
        "A step contradicts its ui_node_id when its text names a node of another console and not its own node. "
        "Steps that paraphrase without naming a node are not counted as contradictions."
    )
    with st.expander("ID-Text Consistency details"):
        for detail in consistency.get("details", []):
            case_id = detail.get("tc_id", "") or "Test case"
            st.write(f"**{case_id} — {'Consistent' if detail.get('consistent') else 'Contradiction'}**")
            for contradiction in detail.get("contradictions", []):
                st.caption(
                    f"{contradiction.get('ui_node_id')} ({contradiction.get('node_name')}), but the step names "
                    f'{", ".join(contradiction.get("named_instead", []))}: "{contradiction.get("step", "")}"'
                )
