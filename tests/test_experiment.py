import json

import pandas as pd
import pytest
from conftest import FakeClient
from test_generation import ANSWER

from testcase_generator import checkpoints, config, experiment

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
