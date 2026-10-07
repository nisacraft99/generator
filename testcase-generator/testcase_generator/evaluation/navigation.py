"""Navigation metrics for test cases generated with UI context.

Both metrics read the ``ui_node_id`` values the model attached to its steps and
compare them with ``navigation_targets.json``:

* Navigation Path Correctness checks, per test case, that the base path in
  ``required_per_testcase`` is present in the defined order.
* Target Node Coverage checks, per user story, that every node in
  ``required_across_story`` is reached by at least one test case.

The two node lists are kept separate so that a missing base-path node does not
lower both metrics.
"""

from __future__ import annotations

import re
from typing import Any

from ..ui_model import UiContext
from .text import case_text, normalize_text

NOT_EVALUATED_PATH_NOTE = (
    "Navigation Path Correctness is only evaluated for outputs generated with UI context, "
    "because only those outputs are expected to contain explicit ui_node_id paths. "
    "Outputs without UI context contain natural-language navigation only, which is not reliable enough "
    "for automated path validation against ui_context.json."
)
NOT_EVALUATED_TARGET_NOTE = (
    "Target Node Coverage is only evaluated for outputs generated with UI context. "
    "Without UI context, the LLM does not produce reliable ui_node_id values; mapping natural-language "
    "steps to technical UI nodes would require fragile alias rules and could distort the comparison."
)

# Verbs showing that a step uses a control to trigger a transition. Merely
# checking or inspecting a control does not count.
_ACTIVATION_PATTERNS = [
    r"\bclick(?:s|ed|ing)?\b",
    r"\bselect(?:s|ed|ing)?\b",
    r"\bopen(?:s|ed|ing)?\b",
    r"\bpress(?:es|ed|ing)?\b",
    r"\btap(?:s|ped|ping)?\b",
    r"\bchoose|chooses|chose|chosen|choosing\b",
    r"\bnavigate(?:s|d|ing)?\b",
    r"\bgo to\b",
    r"\baccess(?:es|ed|ing)?\b",
    r"\bfollow(?:s|ed|ing)?\b",
    r"\bsubmit(?:s|ted|ting)?\b",
    r"\bsave(?:s|d|ing)?\b",
    r"\bcancel(?:s|led|ing)?\b",
    r"\baccept(?:s|ed|ing)?\b",
    r"\bdecline(?:s|d|ing)?\b",
    r"\bback\b",
    r"\bsearch(?:es|ed|ing)?\b",
]
_TRANSITION_RESULT_PATTERN = (
    r"\b(open|opens|opened|display|displayed|shown|show|appears|appear|redirect|redirected|"
    r"navigate|navigated|load|loaded|return|returned)\b"
)

_PERMISSION_WORDS = [
    "permission",
    "permissions",
    "access",
    "role",
    "insufficient permissions",
    "not allowed",
    "denied",
    "blocked",
    "disabled",
    "not actionable",
    "not available",
    "not visible",
    "cannot be opened",
    "cannot be accessed",
    "can not be opened",
    "can not be accessed",
]
_NO_VIEW_PHRASES = [
    "cannot view",
    "can not view",
    "not view",
    "cannot see",
    "can not see",
    "not see",
    "cannot access",
    "can not access",
    "not access",
    "cannot be accessed",
    "can not be accessed",
    "not accessible",
    "cannot be opened",
    "can not be opened",
    "not visible",
]
_MODULE_WORDS = ["module", "dashboard", "strategic meeting", "team meeting", "sm module", "tm module"]
_DENIED_ACTION_PHRASES = [
    "cannot create",
    "can not create",
    "not create",
    "cannot initiate",
    "can not initiate",
    "cannot edit",
    "can not edit",
    "not edit",
    "cannot delete",
    "can not delete",
    "not delete",
    "creation is denied",
    "action is denied",
    "prevents opening",
    "no create",
    "no edit",
    "no delete",
]
_DENIED_CONTROL_PHRASES = [
    "button is not available",
    "button is disabled",
    "control is not available",
    "control is disabled",
    "not actionable",
    "access is denied",
    "action is blocked",
    "blocked due to insufficient permissions",
    "denies the action",
]


# --------------------------------------------------------------- path extraction


def _all_steps(test_case: dict[str, Any]) -> list[Any]:
    """Navigation steps followed by test steps, each counted once.

    ``steps`` already holds both lists merged, so it is only used when the two
    separate lists are empty.
    """
    steps = list(test_case.get("navigation_steps", []) or [])
    steps.extend(test_case.get("steps_only", []) or [])
    if not steps:
        steps.extend(test_case.get("steps", []) or [])
    return steps


def relationship_targets(ui: UiContext, node_id: str, step_text: str, expected_text: str) -> list[str]:
    """UI states directly reached when a step activates ``node_id``.

    A target counts only if ``ui_context.json`` models a relationship via this
    node (or, for relationships without a ``via`` node, from this node) and the
    step actually triggers it: either the action uses an activating verb, or the
    expected result names the target as opened or displayed. Parent nodes are
    never added, so a missing navigation step is not completed for the model.
    """
    node_id = str(node_id or "").strip()
    if not node_id or node_id == "LOGIN":
        return []

    action = normalize_text(step_text or "")
    expected = normalize_text(expected_text or "")
    activates = any(re.search(pattern, action) for pattern in _ACTIVATION_PATTERNS)
    expects_transition = bool(re.search(_TRANSITION_RESULT_PATTERN, expected))

    reached: list[str] = []
    for relationship in ui.relationships:
        via = str(relationship.get("via") or "").strip()
        source = str(relationship.get("from") or "").strip()
        target = str(relationship.get("to") or "").strip()
        if target not in ui.node_ids:
            continue

        uses_relationship = (via and node_id == via) or (not via and source and node_id == source)
        if not uses_relationship:
            continue

        target_name = normalize_text(ui.node_names.get(target, ""))
        target_named = bool(target_name and target_name in expected)
        triggered = activates or (target_named and expects_transition)
        if triggered and target != node_id and target not in reached:
            reached.append(target)
    return reached


def navigation_path(ui: UiContext, test_case: dict[str, Any]) -> list[str]:
    """Ordered UI nodes a test case visits, taken from its valid ``ui_node_id`` values.

    Each explicit node is followed by the states it directly reaches (see
    ``relationship_targets``). Consecutive duplicates are collapsed, because
    several steps on the same screen carry the same node; later revisits are kept.
    """
    path: list[str] = []

    def append(node_id: str) -> None:
        if node_id and node_id != "LOGIN" and node_id in ui.node_ids and (not path or path[-1] != node_id):
            path.append(node_id)

    for step in _all_steps(test_case):
        if not isinstance(step, dict):
            continue
        node_id = str(step.get("ui_node_id") or "").strip()
        if not node_id or node_id == "LOGIN" or node_id not in ui.node_ids:
            continue
        append(node_id)
        for target in relationship_targets(ui, node_id, step.get("step", "") or "", step.get("expected", "") or ""):
            append(target)
    return path


def unknown_node_ids(ui: UiContext, test_case: dict[str, Any]) -> list[str]:
    """``ui_node_id`` values that do not exist in ``ui_context.json``."""
    unknown: list[str] = []
    for step in _all_steps(test_case):
        if not isinstance(step, dict):
            continue
        raw_id = step.get("ui_node_id")
        if raw_id in (None, "", "LOGIN"):
            continue
        node_id = str(raw_id).strip()
        if node_id and node_id not in ui.node_ids and node_id not in unknown:
            unknown.append(node_id)
    return unknown


def negative_test_kind(test_case: dict[str, Any]) -> str:
    """Classify a test case for the navigation metrics.

    * ``"no_access"``: the role cannot open the module at all, so no path to the
      feature is expected. Excluded from Navigation Path Correctness.
    * ``"base_only"``: the role reaches the feature area, but an action there is
      denied. Evaluated like a positive test against the base path.
    * ``"none"``: any other test case.
    """
    text = case_text(test_case)
    is_negative_type = "negative" in normalize_text(str(test_case.get("type", "")))
    names_restricted_role = any(role in text for role in ("manager", "agent"))

    if (
        names_restricted_role
        and any(word in text for word in _MODULE_WORDS)
        and any(phrase in text for phrase in _NO_VIEW_PHRASES)
    ):
        return "no_access"

    has_permission_wording = any(word in text for word in _PERMISSION_WORDS)
    denies_action = any(phrase in text for phrase in _DENIED_ACTION_PHRASES) or any(
        phrase in text for phrase in _DENIED_CONTROL_PHRASES
    )
    if (is_negative_type or has_permission_wording) and names_restricted_role and denies_action:
        return "base_only"
    return "none"


def is_ordered_subsequence(expected: list[str], actual: list[str]) -> bool:
    """True if all expected nodes appear in ``actual`` in the same order."""
    position = 0
    for node in actual:
        if position < len(expected) and node == expected[position]:
            position += 1
    return position == len(expected)


# ----------------------------------------------------------------------- targets


def _node_list(values: Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, list):
        return [str(value) for value in values if str(value).strip()]
    return [str(values)]


def find_targets(navigation_targets: dict[str, Any], story_id: str) -> dict[str, Any] | None:
    """Navigation targets of a user story; the ID is matched case-insensitively."""
    direct = navigation_targets.get(story_id.strip())
    if direct:
        return direct
    for key, value in navigation_targets.items():
        if str(key).strip().lower() == story_id.strip().lower():
            return value
    return None


# ----------------------------------------------------------------------- metrics


def path_not_evaluated() -> dict[str, Any]:
    """Placeholder result for outputs generated without UI context."""
    return {
        "correctness_pct": None,
        "correct_count": None,
        "evaluated_count": None,
        "skipped_count": None,
        "details": [],
        "note": NOT_EVALUATED_PATH_NOTE,
    }


def target_nodes_not_evaluated() -> dict[str, Any]:
    """Placeholder result for outputs generated without UI context."""
    return {
        "coverage_pct": None,
        "covered_count": None,
        "total_count": None,
        "actual_nodes": [],
        "expected_nodes": [],
        "missing_nodes": [],
        "details": [],
        "note": NOT_EVALUATED_TARGET_NOTE,
    }


def evaluate_navigation_path(
    ui: UiContext,
    navigation_targets: dict[str, Any],
    story_id: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Navigation Path Correctness: correct test cases / evaluable test cases * 100.

    A test case is correct when every ``required_per_testcase`` node occurs in
    its path in the defined order and it uses no unknown ``ui_node_id``. Further
    known nodes may occur before, between or after the required ones. No-access
    permission tests are skipped; stories without a base path are not evaluable.
    """
    targets = find_targets(navigation_targets, story_id)
    if not targets:
        return _empty_path_result(f"No navigation targets found for {story_id}")

    base_path = _node_list(targets.get("required_per_testcase"))
    if not base_path and not _node_list(targets.get("required_across_story")):
        return _empty_path_result(f"No target definitions found for {story_id}")

    title = str(targets.get("title") or "Navigation target")
    evaluated = correct = skipped = 0
    details = []

    for case in cases:
        actual = navigation_path(ui, case)
        unknown = unknown_node_ids(ui, case)
        kind = negative_test_kind(case)
        detail = {
            "tc_id": case.get("id", ""),
            "actual": actual,
            "expected": base_path,
            "selected_target": title,
            "can_evaluate": False,
            "is_correct": False,
            "missing_nodes": [],
            "order_ok": False,
            "invalid_ui_node_ids": unknown,
            "skip_reason": "",
        }

        if kind == "no_access":
            skipped += 1
            detail["skip_reason"] = "No-access permission test: no path to the feature is expected."
            details.append(detail)
            continue

        if kind == "base_only":
            detail["selected_target"] = f"{title} — base navigation"
        detail["can_evaluate"] = bool(base_path)
        detail["order_ok"] = is_ordered_subsequence(base_path, actual)
        detail["missing_nodes"] = [node for node in base_path if node not in actual]

        if detail["can_evaluate"]:
            evaluated += 1
            detail["is_correct"] = detail["order_ok"] and not detail["missing_nodes"] and not unknown
            correct += detail["is_correct"]
        else:
            detail["skip_reason"] = "No per-testcase navigation path is defined."
        details.append(detail)

    if evaluated:
        note = None
    elif skipped:
        note = "No evaluable navigation paths remained after excluding no-access permission tests."
    else:
        note = "No evaluable navigation test cases found."

    return {
        "correctness_pct": round(correct / evaluated * 100, 2) if evaluated else None,
        "correct_count": correct,
        "evaluated_count": evaluated,
        "skipped_count": skipped,
        "details": details,
        "note": note,
    }


def _empty_path_result(note: str) -> dict[str, Any]:
    return {
        "correctness_pct": None,
        "correct_count": None,
        "evaluated_count": None,
        "skipped_count": 0,
        "details": [],
        "note": note,
    }


def evaluate_target_node_coverage(
    ui: UiContext,
    navigation_targets: dict[str, Any],
    story_id: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Target Node Coverage: reached ``required_across_story`` nodes / all of them * 100.

    A node counts as reached when any test case that is not a denied-permission
    test has it in its path. This shows that the feature nodes are reached; it
    does not show that the base path is correct, which Navigation Path
    Correctness measures.
    """
    targets = find_targets(navigation_targets, story_id)
    if not targets:
        return _empty_target_result(f"No target nodes found for {story_id}")

    expected: list[str] = []
    for node in _node_list(targets.get("required_across_story")):
        node = node.strip()
        if node and node not in expected:
            expected.append(node)
    if not expected:
        return _empty_target_result(f"No required target node definitions found for {story_id}")

    reached: list[str] = []
    for case in cases:
        if negative_test_kind(case) != "none":
            continue
        for node in navigation_path(ui, case):
            if node not in reached:
                reached.append(node)

    covered = [node for node in expected if node in reached]
    return {
        "coverage_pct": round(len(covered) / len(expected) * 100, 2),
        "covered_count": len(covered),
        "total_count": len(expected),
        "actual_nodes": reached,
        "expected_nodes": expected,
        "missing_nodes": [node for node in expected if node not in reached],
        "details": [{"node_id": node, "node_name": ui.name_of(node), "covered": node in covered} for node in expected],
        "note": None,
    }


def _empty_target_result(note: str) -> dict[str, Any]:
    return {
        "coverage_pct": None,
        "covered_count": None,
        "total_count": None,
        "actual_nodes": [],
        "expected_nodes": [],
        "missing_nodes": [],
        "details": [],
        "note": note,
    }
