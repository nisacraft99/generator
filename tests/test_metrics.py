from conftest import make_case, step

from testcase_generator.evaluation.navigation import (
    evaluate_navigation_path,
    evaluate_target_node_coverage,
    navigation_path,
    negative_test_kind,
)
from testcase_generator.evaluation.role_coverage import evaluate_role_coverage, step_logs_in_as
from testcase_generator.evaluation.text_checks import evaluate_console_naming, evaluate_id_text_consistency

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
    assert result["correctness_pct_without_skipping"] == 0.0


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


def test_step_text_naming_another_console_contradicts_its_node_id(ui):
    wrong_text = [EDIT_TM[0], dict(EDIT_TM[1], step="Open Operations.")] + EDIT_TM[2:]
    result = evaluate_id_text_consistency(ui, [make_case(EDIT_TM, "TC-1"), make_case(wrong_text, "TC-2")])
    assert result["consistency_pct"] == 50.0
    contradiction = result["details"][1]["contradictions"][0]
    assert contradiction["ui_node_id"] == "CONSOLE-C" and contradiction["named_instead"] == ["Operations"]


def test_paraphrased_steps_are_consistent(ui):
    paraphrased = [
        step("Open the console for team coordination.", "CONSOLE-C"),
        step("Press the search button.", "EL-TM-SEARCH-BTN"),
        step("Pick a calendar date for the deadline.", "MOD-TM-CREATE"),
        step("Click TM ID Link in TM List.", "EL-TM-ID"),
    ]
    assert evaluate_id_text_consistency(ui, [make_case(paraphrased)])["consistency_pct"] == 100.0


def test_console_naming_reads_only_the_step_text(ui, navigation_targets):
    without_ids = [dict(entry, ui_node_id=None) for entry in EDIT_TM]
    generic = [step("Log in as Manager."), step("Open the Team Meeting module and assess the performance.")]
    result = evaluate_console_naming(
        ui, navigation_targets, "US-12", [make_case(without_ids, "TC-1"), make_case(generic, "TC-2")]
    )
    assert result["expected_console"] == "Coordination"
    assert [detail["named"] for detail in result["details"]] == [True, False]
    assert result["named_pct"] == 50.0


def test_console_naming_needs_a_console_at_the_start_of_the_base_path(ui, navigation_targets):
    assert evaluate_console_naming(ui, navigation_targets, "US-25", [make_case(EDIT_TM)])["named_pct"] is None
