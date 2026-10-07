"""Acceptance Criteria Coverage, judged by a second LLM (LLM-as-a-Judge).

Each acceptance criterion is judged on its own against the complete generated
test case set. The judge sees titles, steps and expected results, but no
``ui_node_id`` values.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from .. import config
from ..resources import load_prompt
from .text import acceptance_criteria_lines


def format_test_cases(cases: list[dict[str, Any]]) -> str:
    """Plain-text rendering of the test cases as shown to the judge."""
    blocks = []
    for case in cases:
        lines = [f"[{case.get('id', '')}] {case.get('title', '')}"]
        for step in case.get("steps", []) or []:
            if isinstance(step, dict):
                lines.append(f"  Step: {step.get('step', '')}")
                lines.append(f"  Expected: {step.get('expected', '')}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def judge_criterion(client: Any, criterion: str, test_cases_text: str) -> tuple[bool, str]:
    """Ask the judge whether one criterion is covered. Returns (covered, reason)."""
    payload = {"acceptance_criterion": criterion, "generated_test_cases": test_cases_text}
    response = client.chat.completions.create(
        model=config.JUDGE_MODEL,
        reasoning_effort=config.JUDGE_REASONING_EFFORT,
        max_completion_tokens=config.JUDGE_MAX_COMPLETION_TOKENS,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": load_prompt(config.JUDGE_PROMPT_PATH)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw, flags=re.S).strip()
    result = json.loads(raw)
    if "covered" not in result:
        raise ValueError("Judge response has no 'covered' field.")
    reason = str(result.get("reason", "")).strip() or "No reason returned by judge."
    return bool(result.get("covered", False)), reason


def _is_reusable(cached: Any, criterion: str) -> bool:
    return (
        isinstance(cached, dict)
        and cached.get("status") == "complete"
        and cached.get("judge_version") == config.JUDGE_VERSION
        and cached.get("ac_text") == criterion
    )


def evaluate_ac_coverage(
    client: Any,
    cases: list[dict[str, Any]],
    ac_blob: str,
    judge_state: dict[str, Any] | None = None,
    persist: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Share of acceptance criteria the judge marks as covered.

    ``judge_state`` caches the judgement of every criterion (it is the
    ``ac_judge`` entry of a bulk run) and ``persist`` writes it to disk after
    each judge call. An interrupted run therefore only repeats criteria that are
    missing or failed. Judgements made with another JUDGE_VERSION, or for a
    criterion whose text has changed, are not reused.

    If a judge call fails, the result stays incomplete (``overall_pct`` is None)
    instead of counting the criterion as not covered.
    """
    if not client:
        return _unavailable("LLM judge not available (missing API client).")
    criteria = acceptance_criteria_lines(ac_blob)
    if not criteria:
        return _unavailable("No acceptance criteria text provided for LLM judge.")

    cache: dict[str, Any] = {}
    if judge_state is not None:
        judge_state["judge_version"] = config.JUDGE_VERSION
        cache = judge_state.setdefault("details", {})

    test_cases_text = format_test_cases(cases)
    details = []
    covered_count = failed_count = 0

    for index, criterion in enumerate(criteria, start=1):
        ac_id = f"AC-{index}"
        cached = cache.get(ac_id)

        if _is_reusable(cached, criterion):
            covered, reason = bool(cached.get("covered", False)), str(cached.get("reason", ""))
        else:
            try:
                covered, reason = judge_criterion(client, criterion, test_cases_text)
                status = "complete"
            except Exception as error:
                covered, reason = None, f"Judge call failed: {error}"
                status = "failed"
                failed_count += 1
            cache[ac_id] = {
                "status": status,
                "judge_version": config.JUDGE_VERSION,
                "judge_model": config.JUDGE_MODEL,
                "ac_text": criterion,
                "covered": covered,
                "reason": reason,
            }
            if persist is not None:
                persist()

        if covered:
            covered_count += 1
        details.append(
            {
                "ac_id": ac_id,
                "ac_text": criterion,
                "covered": covered,
                "reason": reason,
                "score": None if covered is None else (1.0 if covered else 0.0),
            }
        )

    note = None
    if failed_count:
        note = (
            f"AC Coverage incomplete: {failed_count} judge call(s) failed. "
            "Successful AC judgements were checkpointed and will not be repeated; "
            "resume the bulk evaluation to retry only the failed ACs."
        )
    return {
        "overall_pct": None if failed_count else round(covered_count / len(criteria) * 100, 2),
        "covered_count": None if failed_count else covered_count,
        "total_count": len(criteria),
        "details": details,
        "note": note,
    }


def _unavailable(note: str) -> dict[str, Any]:
    return {"overall_pct": None, "covered_count": None, "total_count": None, "details": [], "note": note}
