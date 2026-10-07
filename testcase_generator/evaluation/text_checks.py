"""Two metrics that read the step text a tester actually sees.

The navigation metrics in ``navigation`` check the ``ui_node_id`` values. These
are invisible to the tester: the exported test design shows only the step and
its expected result. The metrics here close that gap.

* ID-Text Consistency (with UI context): does a step's text contradict the node
  its ``ui_node_id`` points to?
* Console Naming (both variants): does a test case name the console that leads
  to the feature? This is the only navigation measure available without
  ``ui_node_id`` values, so it is the one that compares the two variants.
"""

from __future__ import annotations

import re
from typing import Any

from ..ui_model import UiContext
from .navigation import find_targets

NOT_EVALUATED_CONSISTENCY_NOTE = (
    "ID-Text Consistency is only evaluated for outputs generated with UI context, "
    "because only those outputs contain ui_node_id values."
)


def _steps(test_case: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for step in test_case.get("steps", []) or [] if isinstance(step, dict)]


# ---------------------------------------------------------------- ID-Text Consistency


def step_contradiction(ui: UiContext, step: dict[str, Any]) -> list[str]:
    """Nodes of another console that the step text names instead of its own node.

    A step contradicts its ``ui_node_id`` when its action text names a node that
    belongs to a different console and does not name its own node, for example
    ``CONSOLE-C`` (Coordination) with the text "Open Operations". A paraphrase
    that names no node at all ("Click the search button") is not a contradiction,
    and neither is naming further nodes of the same console.
    """
    node_id = str(step.get("ui_node_id") or "").strip()
    own_console = ui.console_of(node_id) if node_id in ui.node_ids else None
    if own_console is None:
        return []

    named = ui.nodes_named_in(str(step.get("step", "") or ""))
    if node_id in named:
        return []
    return [other for other in named if ui.console_of(other) not in (None, own_console)]


def evaluate_id_text_consistency(ui: UiContext, cases: list[dict[str, Any]]) -> dict[str, Any]:
    """ID-Text Consistency: test cases without a contradicting step / test cases with node IDs * 100."""
    details = []
    for case in cases:
        steps_with_node = [step for step in _steps(case) if str(step.get("ui_node_id") or "").strip() in ui.node_ids]
        if not steps_with_node:
            continue
        contradictions = []
        for step in steps_with_node:
            named = step_contradiction(ui, step)
            if named:
                node_id = str(step["ui_node_id"]).strip()
                contradictions.append(
                    {
                        "ui_node_id": node_id,
                        "node_name": ui.name_of(node_id),
                        "step": step.get("step", ""),
                        "named_instead": [ui.name_of(node_id) for node_id in named],
                    }
                )
        details.append(
            {"tc_id": case.get("id", ""), "consistent": not contradictions, "contradictions": contradictions}
        )

    consistent = sum(detail["consistent"] for detail in details)
    return {
        "consistency_pct": round(consistent / len(details) * 100, 2) if details else None,
        "consistent_count": consistent,
        "total_count": len(details),
        "details": details,
        "note": None if details else "No test case contains a valid ui_node_id.",
    }


def consistency_not_evaluated() -> dict[str, Any]:
    """Placeholder result for outputs generated without UI context."""
    return {
        "consistency_pct": None,
        "consistent_count": None,
        "total_count": None,
        "details": [],
        "note": NOT_EVALUATED_CONSISTENCY_NOTE,
    }


# ----------------------------------------------------------------------- Console Naming


def consoles_named(ui: UiContext, test_case: dict[str, Any]) -> list[str]:
    """Consoles whose name occurs in the action text of any step.

    The match is case-sensitive and on whole words, because a console name such
    as "Performance" is also an ordinary word ("assess the performance").
    """
    text = "\n".join(str(step.get("step", "") or "") for step in _steps(test_case))
    return [
        console_id
        for console_id, name in ui.console_names.items()
        if name and re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", text)
    ]


def evaluate_console_naming(
    ui: UiContext,
    navigation_targets: dict[str, Any],
    story_id: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Console Naming: test cases that name the feature's console / all test cases * 100.

    The expected console is the first node of ``required_per_testcase``. Only
    the step text is read, so the metric is computed the same way for outputs
    with and without UI context.
    """
    targets = find_targets(navigation_targets, story_id) or {}
    base_path = targets.get("required_per_testcase") or []
    expected = str(base_path[0]) if base_path else ""
    if expected not in ui.console_names:
        return {
            "named_pct": None,
            "named_count": None,
            "total_count": None,
            "expected_console": None,
            "details": [],
            "note": f"No console is defined as the start of the navigation path for {story_id}.",
        }

    details = []
    for case in cases:
        named = consoles_named(ui, case)
        details.append(
            {
                "tc_id": case.get("id", ""),
                "named": expected in named,
                "consoles_named": [ui.console_names[console_id] for console_id in named],
            }
        )

    named_count = sum(detail["named"] for detail in details)
    return {
        "named_pct": round(named_count / len(details) * 100, 2) if details else None,
        "named_count": named_count,
        "total_count": len(details),
        "expected_console": ui.console_names[expected],
        "details": details,
        "note": None if details else "No test cases to evaluate.",
    }
