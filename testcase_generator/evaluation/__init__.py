"""Automated evaluation of a generated test case set."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..resources import Resources
from .ac_coverage import evaluate_ac_coverage
from .navigation import (
    evaluate_navigation_path,
    evaluate_target_node_coverage,
    path_not_evaluated,
    target_nodes_not_evaluated,
)
from .role_coverage import evaluate_role_coverage
from .text_checks import consistency_not_evaluated, evaluate_console_naming, evaluate_id_text_consistency

__all__ = ["evaluate_test_cases"]


def evaluate_test_cases(
    resources: Resources,
    story_id: str,
    story: str,
    ac_blob: str,
    cases: list[dict[str, Any]],
    use_ui_context: bool,
    judge_state: dict[str, Any] | None = None,
    persist: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Compute all metrics for one generated output.

    Acceptance Criteria Coverage, Role Coverage and Console Naming are computed
    for both variants. Target Node Coverage, Navigation Path Correctness and
    ID-Text Consistency need ``ui_node_id`` values and are therefore only
    computed for outputs generated with UI context.
    """
    ac = evaluate_ac_coverage(resources.client, story, cases, ac_blob, judge_state, persist)

    if use_ui_context:
        target_node = evaluate_target_node_coverage(resources.ui_context, resources.navigation_targets, story_id, cases)
        navigation = evaluate_navigation_path(resources.ui_context, resources.navigation_targets, story_id, cases)
        consistency = evaluate_id_text_consistency(resources.ui_context, cases)
    else:
        target_node = target_nodes_not_evaluated()
        navigation = path_not_evaluated()
        consistency = consistency_not_evaluated()

    return {
        "ac": ac,
        "target_node": target_node,
        "navigation_path": navigation,
        "role": evaluate_role_coverage(story, ac_blob, cases),
        "id_text_consistency": consistency,
        "console_naming": evaluate_console_naming(resources.ui_context, resources.navigation_targets, story_id, cases),
    }
