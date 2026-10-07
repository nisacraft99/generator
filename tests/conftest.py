"""Shared fixtures: the project's UI context and a scripted stand-in for the OpenAI client."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from testcase_generator import config  # noqa: E402
from testcase_generator.resources import Resources, load_json  # noqa: E402
from testcase_generator.ui_model import UiContext  # noqa: E402


class FakeClient:
    """Returns the queued generator answers in order and judges every criterion as covered."""

    def __init__(self, generator_answers):
        self.generator_answers = list(generator_answers)
        self.generator_calls = 0
        self.judge_calls = 0
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **request):
        self.requests.append(request)
        if request["model"] == config.GENERATOR_MODEL:
            self.generator_calls += 1
            content = self.generator_answers.pop(0)
        else:
            self.judge_calls += 1
            content = json.dumps({"covered": True, "reason": "covered by TC-1"})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def ui():
    return UiContext(load_json(config.UI_CONTEXT_PATH, {}))


@pytest.fixture
def navigation_targets():
    return load_json(config.NAVIGATION_TARGETS_PATH, {})


@pytest.fixture
def make_resources(ui, navigation_targets):
    def build(client):
        return Resources(client=client, ui_context=ui, navigation_targets=navigation_targets)

    return build


def step(text, node_id=None, expected=""):
    return {"step": text, "expected": expected, "ui_node_id": node_id}


def make_case(steps, case_id="TC-1", title="Edit a Team Meeting", case_type="Functional"):
    """A test case in the internal shape produced by the generator."""
    return {
        "id": case_id,
        "title": title,
        "priority": "High",
        "type": case_type,
        "navigation_steps": steps,
        "steps_only": [],
        "steps": steps,
    }
