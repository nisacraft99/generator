import json

from conftest import FakeClient

from testcase_generator import config
from testcase_generator.generation import (
    INVALID_JSON,
    generate_test_cases,
    generation_failure,
    parse_model_json,
)

ANSWER = {
    "test_cases": [
        {
            "id": "TC-1",
            "title": "Create SM",
            "priority": "High",
            "type": "Functional",
            "navigation_steps": [{"step": "Log in as Director.", "expected": "Logged in.", "ui_node_id": None}],
            "steps": [{"step": "Click Create SM Button.", "expected": "Popup opens.", "ui_node_id": "EL-SM-CREATE"}],
        }
    ],
    "open_questions": ["Which date format?", {"question": "Which locale?"}],
}


def test_parse_accepts_fences_surrounding_text_and_trailing_commas():
    assert parse_model_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_model_json('Here it is: {"a": [1, 2,],} Thanks') == {"a": [1, 2]}
    assert parse_model_json("{'a': True, 'b': None}") == {"a": True, "b": None}


def test_parse_reports_invalid_json_instead_of_raising():
    assert parse_model_json("no json here") == {"test_cases": [], "open_questions": [INVALID_JSON]}
    assert generation_failure([INVALID_JSON]) == INVALID_JSON
    assert generation_failure(["Which date format?"]) == ""


def test_generate_merges_navigation_and_test_steps():
    cases, open_questions = generate_test_cases(FakeClient([json.dumps(ANSWER)]), "As a Director ...", "AC 1\nAC 2")
    assert [step["step"] for step in cases[0]["steps"]] == ["Log in as Director.", "Click Create SM Button."]
    assert cases[0]["steps_only"][0]["ui_node_id"] == "EL-SM-CREATE"
    assert open_questions == ["Which date format?", '{"question": "Which locale?"}']


def test_variants_differ_only_in_the_ui_context_of_the_input():
    client = FakeClient([json.dumps(ANSWER)] * 2)
    generate_test_cases(client, "As a Director ...", "AC 1")
    generate_test_cases(client, "As a Director ...", "AC 1", ui_context={"nodes": []})
    without_ui, with_ui = client.requests

    assert without_ui["messages"][0] == with_ui["messages"][0]
    assert without_ui["model"] == with_ui["model"] == config.GENERATOR_MODEL
    payload_without, payload_with = (json.loads(request["messages"][1]["content"]) for request in client.requests)
    assert "ui_context" not in payload_without
    assert payload_with == {**payload_without, "ui_context": {"nodes": []}}


def test_missing_client_is_a_technical_failure():
    cases, open_questions = generate_test_cases(None, "story", "AC")
    assert cases == [] and generation_failure(open_questions)
