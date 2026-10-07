import json

import pandas as pd
import pytest
from conftest import FakeClient
from test_generation import ANSWER

from testcase_generator import checkpoints, config, experiment
from testcase_generator.resources import Resources
from testcase_generator.ui_model import UiContext

STORIES = [
    {
        "id": "US-1",
        "title": "Create SM",
        "story": "As a Director I want to create a Strategic Meeting",
        "ac_blob": "a popup appears\nonly a user with the role director can create an SM",
        "acceptance_criteria_count": 2,
    }
]


@pytest.fixture(autouse=True)
def checkpoint_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHECKPOINT_DIR", tmp_path)
    return tmp_path


def test_bulk_run_evaluates_both_variants(make_resources):
    client = FakeClient([json.dumps(ANSWER)] * 2)
    result = experiment.run_bulk_evaluation(make_resources(client), STORIES, repetitions=1)

    assert list(result.rows["variant"]) == [config.VARIANT_WITHOUT_UI, config.VARIANT_WITH_UI]
    assert list(result.rows["ac_coverage_pct"]) == [100.0, 100.0]
    assert result.rows["navigation_path_correctness_pct"].isna().tolist() == [True, False]
    assert result.stats == {"completed": 2, "generated": 2, "judge_done": 4, "judge_failed": 0}


def test_checkpoint_documents_settings_and_every_model_call(make_resources):
    client = FakeClient([json.dumps(ANSWER)] * 2)
    result = experiment.run_bulk_evaluation(make_resources(client), STORIES, repetitions=1)
    checkpoint = checkpoints.load(result.checkpoint_path)

    assert checkpoint["settings"]["generator_model"] == config.GENERATOR_MODEL
    assert checkpoint["settings"]["generator_temperature"] == config.GENERATOR_TEMPERATURE
    assert len(checkpoint["settings"]["ui_context_sha256"]) == 64
    for run in checkpoint["runs"].values():
        assert json.loads(run["generation"]["raw_response"]) == ANSWER and run["generation"]["attempts"] == 1
        assert all(judgement["judged_at"] for judgement in run["ac_judge"]["details"].values())


def test_changed_ui_context_starts_a_new_checkpoint(make_resources, ui, navigation_targets):
    resources = make_resources(FakeClient([]))
    smaller_ui = UiContext({**ui.raw, "nodes": ui.raw["nodes"][:-1]})
    changed = Resources(client=resources.client, ui_context=smaller_ui, navigation_targets=navigation_targets)
    assert experiment.checkpoint_path(resources, STORIES, 1) != experiment.checkpoint_path(changed, STORIES, 1)


def test_changed_judge_prompt_judges_again_without_generating(make_resources, tmp_path, monkeypatch):
    experiment.run_bulk_evaluation(make_resources(FakeClient([json.dumps(ANSWER)] * 2)), STORIES, repetitions=1)

    new_prompt = tmp_path / "judge.txt"
    new_prompt.write_text("You are a lenient reviewer.", encoding="utf-8")
    monkeypatch.setattr(config, "JUDGE_PROMPT_PATH", new_prompt)
    client = FakeClient([])
    experiment.run_bulk_evaluation(make_resources(client), STORIES, repetitions=1)
    assert client.generator_calls == 0 and client.judge_calls == 4


def test_resume_repeats_neither_generation_nor_judge_calls(make_resources):
    first = FakeClient([json.dumps(ANSWER)] * 2)
    experiment.run_bulk_evaluation(make_resources(first), STORIES, repetitions=1)

    second = FakeClient([])
    result = experiment.run_bulk_evaluation(make_resources(second), STORIES, repetitions=1)
    assert second.generator_calls == 0 and second.judge_calls == 0
    assert result.stats["completed"] == 2


def test_invalid_json_is_regenerated_and_never_scored(make_resources):
    retries = config.MAX_INVALID_JSON_RETRIES
    client = FakeClient(["not json"] * (retries + 1) + ["not json", json.dumps(ANSWER)])
    result = experiment.run_bulk_evaluation(make_resources(client), STORIES, repetitions=1)

    failed, recovered = result.rows.to_dict("records")
    assert pd.isna(failed["ac_coverage_pct"]) and "Automatic regeneration also failed" in failed["error"]
    assert recovered["ac_coverage_pct"] == 100.0 and recovered["error"] == ""
    assert client.generator_calls == retries + 3


def test_reevaluation_generates_nothing(make_resources, checkpoint_dir):
    client = FakeClient([json.dumps(ANSWER)] * 2)
    path = experiment.run_bulk_evaluation(make_resources(client), STORIES, repetitions=1).checkpoint_path
    checkpoint = checkpoints.load(path)

    client = FakeClient([])
    result = experiment.reevaluate_checkpoint(make_resources(client), checkpoint, checkpoint_dir / "copy.json")
    assert client.generator_calls == 0 and client.judge_calls == 0
    assert list(result.rows["ac_coverage_pct"]) == [100.0, 100.0]
    assert experiment.load_saved_results(checkpoint).rows.equals(result.rows)


def test_judge_receives_the_user_story_as_context(make_resources):
    client = FakeClient([json.dumps(ANSWER)] * 2)
    experiment.run_bulk_evaluation(make_resources(client), STORIES, repetitions=1)
    judge_inputs = [
        json.loads(request["messages"][1]["content"])
        for request in client.requests
        if request["model"] == config.JUDGE_MODEL
    ]
    assert {payload["user_story"] for payload in judge_inputs} == {STORIES[0]["story"]}
    assert set(judge_inputs[0]) == {"user_story", "acceptance_criterion", "generated_test_cases"}
