"""Central configuration: file locations, model settings and experiment constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROMPT_DIR = PROJECT_ROOT / "prompts"
ASSET_DIR = PROJECT_ROOT / "assets"
CHECKPOINT_DIR = PROJECT_ROOT / ".bulk_checkpoints"

UI_CONTEXT_PATH = DATA_DIR / "ui_context.json"
NAVIGATION_TARGETS_PATH = DATA_DIR / "navigation_targets.json"
USER_STORIES_PATH = DATA_DIR / "bulk_userstories.json"

GENERATOR_PROMPT_PATH = PROMPT_DIR / "generator_system.txt"
JUDGE_PROMPT_PATH = PROMPT_DIR / "judge_system.txt"
STYLESHEET_PATH = ASSET_DIR / "style.css"

# Test case generation.
GENERATOR_MODEL = "gpt-5.6-terra"
GENERATOR_REASONING_EFFORT = "none"
GENERATOR_TEMPERATURE = 1
MAX_INVALID_JSON_RETRIES = 2

# LLM-as-a-Judge for Acceptance Criteria Coverage. Saved judgements are reused
# only while this label, the judge model and the judge prompt are unchanged
# (see evaluation.ac_coverage.judge_version).
JUDGE_MODEL = "gpt-5.6-luna"
JUDGE_REASONING_EFFORT = "none"
JUDGE_MAX_COMPLETION_TOKENS = 500
JUDGE_VERSION = "v4"

# The two experimental variants. They share one prompt; the only difference is
# whether the UI context is part of the model input.
VARIANT_WITH_UI = "with_ui_context"
VARIANT_WITHOUT_UI = "without_ui_context"
VARIANTS = ((VARIANT_WITHOUT_UI, False), (VARIANT_WITH_UI, True))

CHECKPOINT_VERSION = 1

# ---------------------------------------------------------------------------
# Application-specific vocabulary of the system under test (UMS)
# ---------------------------------------------------------------------------

ROLES = ("director", "manager", "agent")

# Wording used to recognise permission tests in which a role cannot open a
# module at all. Such tests have no path to the feature and are skipped by
# Navigation Path Correctness. The detection is keyword-based; see README.
NO_ACCESS_ROLES = ("manager", "agent")
NO_ACCESS_AREA_WORDS = (
    "module",
    "dashboard",
    "strategic meeting",
    "team meeting",
    "sm module",
    "tm module",
)


def variant_name(use_ui_context: bool) -> str:
    return VARIANT_WITH_UI if use_ui_context else VARIANT_WITHOUT_UI
