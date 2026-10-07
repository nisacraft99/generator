from conftest import make_case, step

from testcase_generator.evaluation.navigation import (
    evaluate_navigation_path,
    evaluate_target_node_coverage,
    navigation_path,
    negative_test_kind,
)
from testcase_generator.evaluation.role_coverage import evaluate_role_coverage, step_logs_in_as

EDIT_TM = [
    step("Log in as Manager."),
    step("Open Coordination.", "CONSOLE-C"),
    step("Select Team Meeting.", "OPT-TM", "TM Dashboard is displayed."),
    step("Click the TM ID Link of an existing TM.", "EL-TM-ID", "TM Detail is displayed."),
    step("Click Edit TM Button.", "EL-TM-EDIT", "Edit TM Popup opens."),
    step("Change the title and click save.", "EL-TM-EDIT-SAVE", "The TM is updated."),
]


def test_path_adds_the_screen_a_step_opens_but_no_missing_parents(ui):
    path = navigation_path(ui, make_case(EDIT_TM))
    assert path[:5] == ["CONSOLE-C", "OPT-TM", "SCR-TM-DASHBOARD", "EL-TM-ID", "SCR-TM-DETAIL"]
    assert navigation_path(ui, make_case([step("Click Edit TM Button.", "EL-TM-EDIT")])) == [
        "EL-TM-EDIT",
        "MOD-TM-EDIT",
    ]
    assert navigation_path(ui, make_case([step("Verify Edit TM Button is visible.", "EL-TM-EDIT")])) == ["EL-TM-EDIT"]


def test_navigation_path_is_correct_for_the_right_console(ui, navigation_targets):
    result = evaluate_navigation_path(ui, navigation_targets, "US-12", [make_case(EDIT_TM)])
    assert result["correctness_pct"] == 100.0 and result["evaluated_count"] == 1


def test_wrong_console_makes_the_path_incorrect(ui, navigation_targets):
    wrong = [dict(EDIT_TM[1], ui_node_id="CONSOLE-O", step="Open Operations.")] + EDIT_TM[2:]
    result = evaluate_navigation_path(ui, navigation_targets, "US-12", [make_case(wrong)])
    assert result["correctness_pct"] == 0.0
    assert result["details"][0]["missing_nodes"] == ["CONSOLE-C"]


def test_unknown_node_id_makes_the_path_incorrect(ui, navigation_targets):
    steps = EDIT_TM + [step("Click the magic button.", "EL-DOES-NOT-EXIST")]
    detail = evaluate_navigation_path(ui, navigation_targets, "US-12", [make_case(steps)])["details"][0]
    assert not detail["is_correct"] and detail["invalid_ui_node_ids"] == ["EL-DOES-NOT-EXIST"]


def test_no_access_tests_are_skipped(ui, navigation_targets):
    denied = make_case(
        [step("Log in as Agent."), step("Try to open the SM module.", expected="The agent cannot view the SM module.")],
        title="Agent can not view the SM module",
        case_type="Negative",
    )
    assert negative_test_kind(denied) == "no_access"
    result = evaluate_navigation_path(ui, navigation_targets, "US-1", [denied])
    assert result["skipped_count"] == 1 and result["correctness_pct"] is None


def test_target_node_coverage_counts_reached_feature_nodes(ui, navigation_targets):
    result = evaluate_target_node_coverage(ui, navigation_targets, "US-12", [make_case(EDIT_TM)])
    assert result["expected_nodes"] == ["EL-TM-EDIT", "MOD-TM-EDIT", "EL-TM-EDIT-SAVE"]
    assert result["coverage_pct"] == 100.0

    partial = evaluate_target_node_coverage(ui, navigation_targets, "US-12", [make_case(EDIT_TM[:4])])
    assert partial["covered_count"] == 0 and partial["missing_nodes"] == result["expected_nodes"]


def test_role_coverage_needs_an_explicit_login_step_per_role():
    story = "As a Manager I want to edit a Team Meeting"
    criteria = "a user with the role manager can edit a TM he created\na user with the role director can not edit a TM"
    result = evaluate_role_coverage(story, criteria, [make_case(EDIT_TM)])
    assert result["required_roles"] == ["director", "manager"]
    assert result["missing_roles"] == ["director"] and result["overall_pct"] == 50.0


def test_login_step_counts_only_the_first_role_named():
    assert step_logs_in_as("Log in as Manager and review data for Agent", "manager")
    assert not step_logs_in_as("Log in as Manager and review data for Agent", "agent")
    assert step_logs_in_as("Log in as the assigned Agent", "agent")
