# app.py
# Run:
#   pip install -U streamlit python-dotenv reportlab openai
#   streamlit run app.py

import os
import io
import json
import ast
import re
import hashlib
from typing import Dict, List, Any, Optional

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    Table,
    TableStyle,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ======================= PAGE CONFIG =======================
st.set_page_config(
    page_title="User Story → Testcase Generator",
    page_icon="🧪",
    layout="wide"
)

# ======================= PROFESSIONAL UI =======================
st.markdown("""
<style>
:root {
  --app-bg: #0f172a;
  --panel-bg: #111827;
  --panel-bg-soft: #1f2937;
  --text-main: #e5e7eb;
  --text-muted: #94a3b8;
  --border-main: #334155;
  --accent: #38bdf8;
  --accent-soft: rgba(56, 189, 248, 0.14);
  --input-bg: #020617;
  --button-bg: #2563eb;
  --button-hover: #1d4ed8;
  --font-main: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

html, body, .stApp, .stAppViewContainer, .main, .block-container,
.stMarkdown, .stAlert, .stDataFrame, .stForm,
.stTextInput, .stTextArea, .stSelectbox, .stMultiSelect, .stNumberInput,
.stButton > button, .stDownloadButton > button,
label, p, span, div {
  font-family: var(--font-main) !important;
}

.stApp {
  background: radial-gradient(circle at top left, #1e293b 0, var(--app-bg) 38%, #020617 100%) !important;
  color: var(--text-main) !important;
}

.block-container {
  max-width: 1180px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

.mock-title {
  margin: 18px 0 30px 0;
  width: 100%;
  max-width: 980px;
  background: linear-gradient(135deg, #111827, #1e293b);
  border: 1px solid var(--border-main);
  border-left: 5px solid var(--accent);
  border-radius: 14px;
  text-align: left;
  font-weight: 750;
  font-size: 34px;
  letter-spacing: -0.02em;
  padding: 22px 28px;
  color: var(--text-main);
  box-shadow: 0 20px 45px rgba(2, 6, 23, 0.38);
}

.mock-title::after {
  content: "Professional QA Workspace";
  display: block;
  margin-top: 6px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--text-muted);
}

.mock-label {
  font-weight: 650;
  font-size: 15px;
  color: var(--text-main);
  margin: 20px 0 8px 0;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}

.field-single, .field-multi {
  width: 100%;
  max-width: 980px;
  margin-left: 0;
}

.stTextArea textarea,
.stTextInput input {
  background: var(--input-bg) !important;
  border: 1px solid var(--border-main) !important;
  border-radius: 12px !important;
  color: var(--text-main) !important;
  font-size: 16px !important;
  padding: 12px 14px !important;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.35) !important;
  line-height: 1.5 !important;
}

.stTextArea textarea:focus,
.stTextInput input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-soft) !important;
}

.stTextArea textarea::placeholder,
.stTextInput input::placeholder {
  color: #64748b !important;
}

.singleline textarea {
  min-height: 64px !important;
  max-height: 64px !important;
  resize: none !important;
  overflow: hidden !important;
  white-space: nowrap !important;
}

.export-wrap { margin: 30px 0; }
.export-wrap .stButton > button,
.stButton > button {
  background: var(--button-bg) !important;
  color: #ffffff !important;
  border: 1px solid rgba(147, 197, 253, 0.25) !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 15px !important;
  padding: 0.75rem 1.1rem !important;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.22) !important;
}

.export-wrap .stButton > button:hover,
.stButton > button:hover {
  background: var(--button-hover) !important;
  border-color: var(--accent) !important;
}

.export-wrap .stButton > button:disabled,
.stButton > button:disabled {
  background: #334155 !important;
  color: #94a3b8 !important;
  border-color: #475569 !important;
  box-shadow: none !important;
}

.stDownloadButton > button {
  background: #0f172a !important;
  color: var(--text-main) !important;
  border: 1px solid var(--border-main) !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 15px !important;
  padding: 0.7rem 1rem !important;
}

.stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
  color: var(--text-muted) !important;
}

hr { border-color: var(--border-main) !important; }

[data-testid="stDataFrame"], .stDataFrame {
  border: 1px solid var(--border-main) !important;
  border-radius: 12px !important;
  overflow: hidden;
}

.login-card {
  max-width: 640px;
  margin: 10vh auto 1rem auto;
  padding: 30px;
  border: 1px solid var(--border-main);
  border-radius: 14px;
  background: var(--panel-bg);
  box-shadow: 0 20px 45px rgba(2, 6, 23, 0.45);
}

.login-title {
  color: var(--text-main);
  font-size: 30px;
  font-weight: 750;
  margin-bottom: 8px;
}

.login-note {
  color: var(--text-muted);
  font-size: 15px;
  margin-bottom: 18px;
}
</style>
""", unsafe_allow_html=True)

# ======================= PASSWORD GATE =======================
APP_PASSWORD = st.secrets.get("APP_PASSWORD", os.getenv("APP_PASSWORD", ""))

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

def try_login():
    if st.session_state.get("pw_input", "") == APP_PASSWORD and APP_PASSWORD:
        st.session_state.auth_ok = True
        st.session_state.pop("pw_error", None)
    else:
        st.session_state.pw_error = "Wrong password."

if not st.session_state.auth_ok:
    st.markdown("""
    <div class="login-card">
      <div class="login-title">User Story to Testcase Generator</div>
      <p class="login-note">Private application. Enter the password to continue.</p>
    </div>
    """, unsafe_allow_html=True)

    st.text_input("Password", type="password", key="pw_input")
    st.button("Sign in", on_click=try_login)

    if st.session_state.get("pw_error"):
        st.error(st.session_state["pw_error"])
    st.stop()

# ======================= MAIN UI =======================
st.markdown('<div class="mock-title">User Story → Testcase Generator</div>', unsafe_allow_html=True)

st.markdown('<div class="mock-label">User Story ID (optional; required for evaluation, e.g. US-4)</div>', unsafe_allow_html=True)
us_id = st.text_input(
    "",
    key="us_id_input",
    label_visibility="collapsed",
    placeholder="US-4 (optional)",
    value=""
)

st.markdown('<div class="mock-label">User Story</div>', unsafe_allow_html=True)
st.markdown('<div class="field-single singleline">', unsafe_allow_html=True)
user_story = st.text_area(
    "", key="us_one", label_visibility="hidden",
    placeholder="As a <role>, I want ..., so that ...",
    height=200
)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="mock-label">Acceptance Criteria (one criterion per line)</div>', unsafe_allow_html=True)
st.markdown('<div class="field-multi">', unsafe_allow_html=True)
ac_text = st.text_area(
    "", key="ac_lines", label_visibility="hidden",
    placeholder="• Criterion 1\n• Criterion 2\n• Criterion 3",
    height=400
)
st.markdown('</div>', unsafe_allow_html=True)

# ======================= FILE LOADERS =======================
UI_CONTEXT_PATH = "ui_context.json"
NAV_TARGETS_PATH = "navigation_targets.json"
BULK_USERSTORIES_PATH = "bulk_userstories.json"

def load_json_file(path: str, default: Any):
    """Load a JSON file from the app folder.

    The canonical names are ui_context.json, navigation_targets.json and bulk_userstories.json.
    For local experiments and ChatGPT-uploaded files, this also accepts
    suffixed copies such as navigation_targets(4).json and picks the newest matching file.
    """
    candidate_paths = [path]
    base, ext = os.path.splitext(path)
    try:
        same_dir = os.listdir(".")
        suffixed = [name for name in same_dir if name.startswith(base + "(") and name.endswith(ext)]
        suffixed.sort(key=lambda name: os.path.getmtime(name), reverse=True)
        candidate_paths.extend(suffixed)
    except Exception:
        pass

    for candidate in candidate_paths:
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return default

UI_CONTEXT = load_json_file(UI_CONTEXT_PATH, {})
NAV_TARGETS = load_json_file(NAV_TARGETS_PATH, {})

st.caption(f"UI context loaded nodes: {len(UI_CONTEXT.get('nodes', [])) if isinstance(UI_CONTEXT, dict) else 0}")
st.caption(f"Navigation targets loaded: {len(NAV_TARGETS) if isinstance(NAV_TARGETS, dict) else 0}")

# ======================= OPENAI SETUP =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

# Models used in the experiment. Keep these centralized so generation,
# evaluation and checkpoint fingerprints always stay consistent.
GENERATOR_MODEL = "gpt-5.6-terra"
GENERATOR_REASONING_EFFORT = "none"

SYSTEM_PROMPT_BASE = """
You are a senior test engineer.
Return ONLY valid JSON (no markdown, no prose).

TASK:
Generate manual test cases from the provided user story and acceptance criteria.
The only experimental difference between the two variants is whether the payload contains ui_context.

INPUTS:
- story: the user story.
- acceptance_criteria: list of acceptance criteria.
- ui_context: optional JSON with nodes and relationships of the application UI.

UI CONTEXT RULES:
- If ui_context is provided, use only nodes and relationships from ui_context for concrete navigation.
- If ui_context is provided, do NOT invent menus, workspaces, screens, buttons, fields, popups, modules, or navigation paths that are not present in ui_context.nodes.
- If ui_context is provided, every concrete UI step SHOULD include a ui_node_id that exactly matches an existing ui_context.nodes[].id.
- If ui_context is not provided, do NOT invent concrete UI names or ui_node_id values. In that case use ui_node_id:null and keep navigation generic.
- Generic steps like "go to the function" are not allowed when ui_context provides concrete path elements.
- If ui_context is provided, do not combine workspace opening and navigation option selection in one step. Use separate steps, e.g. first open the workspace node, then select the module/nav option node.
- If ui_context is provided, preserve the UI order from relationships/parents: workspace -> navigation option -> dashboard/screen -> clickable element -> resulting screen/modal.

UI NAMING RULES:
- If ui_context is provided, use the UI names exactly as they appear in ui_context.
- If ui_context is provided, concrete workspace, module, screen, popup, button and field names must come from ui_context.nodes.
- If ui_context is not provided, do not use or invent concrete workspace, menu, screen, popup, button or field names that are not stated in the user story or acceptance criteria.
- If ui_context is not provided, keep setup/navigation generic, for example: open the relevant module, open the selected item, or open the detail view.
- Do not use ui_node_id values unless ui_context is provided.

ROLE AND NAVIGATION RULES:
- Login role and UI location are separate concepts.
- The login role determines permissions.
- If ui_context is provided, the UI context determines where a feature is located.
- If ui_context is not provided, do not infer hidden application structure beyond the user story and acceptance criteria.
- For negative permission tests, verify that the logged-in role cannot perform the restricted action.
- If a role has viewing permission but not create/edit/delete permission, test the missing control, disabled control, or denied action. Do not replace the role with another role.

TEST CASE GRANULARITY RULES:
- Give one focused test case per acceptance criterion whenever possible.
- If fewer test cases are generated than acceptance criteria, this is usually invalid unless multiple acceptance criteria are inseparably linked.
- Do NOT merge unrelated acceptance criteria into one test case.
- Keep negative role/permission tests separate from positive functional tests.
- Keep navigation/setup and test logic in the same test case output.

ROLE COVERAGE RULES:
- The test cases must cover all roles mentioned as actors or permission rules in the user story and acceptance criteria.
- Do NOT combine multiple roles into one actor step such as "Log in as Manager/Agent".
- If both Manager and Agent must be tested, create separate test cases or separate explicit steps for each role.
- Use explicit actor steps such as "Log in as Manager" and "Log in as Agent".

COVERAGE RULES:
- Every acceptance criterion MUST be covered explicitly in the generated test case set.
- If needed, create additional test cases to cover uncovered acceptance criteria.
- Be specific and observable in expected results.

OUTPUT SCHEMA:
{
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional|Negative|Boundary",
      "navigation_steps":[
        {"step":"string","expected":"string","ui_node_id":"string|null"}
      ],
      "steps":[
        {"step":"string","expected":"string","ui_node_id":"string|null"}
      ]
    }
  ],
  "open_questions":[]
}

JSON RULES:
- Return valid JSON only.
- Do not include markdown.
- Do not include code fences.
"""

# Both variants use the same prompt. The only difference is that the with-UI variant receives ui_context in the payload.
SYSTEM_PROMPT_WITH_UI = SYSTEM_PROMPT_BASE
SYSTEM_PROMPT_NO_UI = SYSTEM_PROMPT_BASE

# ======================= GENERATOR HELPERS =======================
def _extract_first_balanced_json_object(text: str) -> Optional[str]:
    """Return the first balanced {...} block while respecting JSON string literals."""
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _json_from_text(txt: str) -> dict:
    """Parse model output locally and salvage common formatting mistakes without another API call."""
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.S | re.I).strip()

    candidates = [txt]
    balanced = _extract_first_balanced_json_object(txt)
    if balanced and balanced != txt:
        candidates.append(balanced)

    # First try strict JSON, then a tiny deterministic repair for trailing commas.
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            data = json.loads(repaired)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # Some models occasionally emit Python-style dict literals (single quotes / True / None).
        # literal_eval is local and safe for literals only; no code is executed.
        try:
            data = ast.literal_eval(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {"test_cases": [], "open_questions": ["Model response was not valid JSON."]}

def _normalize_step(step_obj):
    if isinstance(step_obj, dict):
        return {
            "step": (step_obj.get("step", "") or "").strip(),
            "expected": (step_obj.get("expected", "") or "").strip(),
            "ui_node_id": step_obj.get("ui_node_id", None),
        }
    return {"step": str(step_obj), "expected": "", "ui_node_id": None}

def _clean_open_questions(raw_open_q):
    cleaned = []
    for q in raw_open_q:
        if isinstance(q, str):
            cleaned.append(q)
        elif q is None:
            cleaned.append("Unspecified open question.")
        else:
            cleaned.append(json.dumps(q, ensure_ascii=False))
    return cleaned

def generate_cases(story: str, ac_blob: str, use_ui_context: bool = True):
    if not client:
        return [], ["OpenAI client not initialized (missing OPENAI_API_KEY or openai package)."]
    if not story.strip():
        return [], ["User story is empty."]

    payload = {
        "story": story.strip(),
        "acceptance_criteria": [l.strip() for l in ac_blob.splitlines() if l.strip()],
    }

    system_prompt = SYSTEM_PROMPT_WITH_UI if use_ui_context else SYSTEM_PROMPT_NO_UI
    if use_ui_context:
        payload["ui_context"] = UI_CONTEXT

    try:
        resp = client.chat.completions.create(
            model=GENERATOR_MODEL,
            reasoning_effort=GENERATOR_REASONING_EFFORT,
            temperature=1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        data = _json_from_text(resp.choices[0].message.content)

        tcs = data.get("test_cases", []) or []
        raw_open_q = data.get("open_questions", []) or []
        open_q = _clean_open_questions(raw_open_q)

        fixed = []
        for tc in tcs:
            nav = [_normalize_step(s) for s in (tc.get("navigation_steps", []) or [])]
            steps = [_normalize_step(s) for s in (tc.get("steps", []) or [])]

            # Keep the output structure comparable for both variants.
            # The only experimental difference is whether ui_context is in the payload.
            # Therefore navigation_steps are merged into the PDF for both variants.
            merged_steps = nav + steps
            merged_steps = [
                s for s in merged_steps
                if (s.get("step") or "").strip() not in {"", "—"}
                or (s.get("expected") or "").strip() not in {"", "—"}
            ]

            fixed.append(
                {
                    "id": (tc.get("id", "") or "").strip(),
                    "title": (tc.get("title", "") or "").strip(),
                    "priority": (tc.get("priority", "") or "").strip(),
                    "type": (tc.get("type", "") or "").strip(),
                    "navigation_steps": nav,
                    "steps_only": steps,
                    "steps": merged_steps,
                }
            )

        return fixed, open_q
    except Exception as e:
        return [], [f"OpenAI call failed: {e}"]

# ======================= EVALUATION HELPERS =======================
ROLE_WORDS = ["director", "manager", "agent"]

def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("„", '"').replace("“", '"').replace("’", "'")
    s = re.sub(r"[^a-z0-9äöüß/\-\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def testcase_full_text(tc: Dict[str, Any]) -> str:
    """Collect title, type, navigation steps, normal steps and expected results."""
    parts = [str(tc.get("title", "")), str(tc.get("type", ""))]
    for key in ["navigation_steps", "steps_only", "steps"]:
        for step in tc.get(key, []) or []:
            if isinstance(step, dict):
                parts.append(str(step.get("step", "")))
                parts.append(str(step.get("expected", "")))
            else:
                parts.append(str(step))
    return normalize_text(" ".join(parts))


# ======================= LLM-AS-A-JUDGE AC EVALUATION =======================

# Judge configuration. GPT-5.6 Luna defaults to medium reasoning; for this short,
# schema-constrained binary judgement we explicitly disable reasoning so the
# completion budget is used for the JSON answer itself.
AC_JUDGE_VERSION = "strict_v2"
AC_JUDGE_MODEL = "gpt-5.6-luna"
AC_JUDGE_REASONING_EFFORT = "none"
AC_JUDGE_MAX_COMPLETION_TOKENS = 500

LLM_JUDGE_SYSTEM_PROMPT = """
You are a strict QA expert evaluating acceptance-criterion coverage.
You receive exactly one acceptance criterion and a set of generated manual test cases.
Decide whether the acceptance criterion is actually TESTED by the generated test cases.

Coverage rules:
- Mark covered=true only if at least one test case explicitly exercises the essential condition/action of the acceptance criterion AND verifies the relevant expected behavior, restriction, or outcome.
- A title, keyword, paraphrase, setup statement, or mere mention of the requirement is NOT enough by itself.
- Do not infer missing test actions or expected results from context.
- Semantic equivalence is allowed; wording does not need to match exactly.
- For permission criteria, the specified role must be used and the allowed/denied behavior must be verified.
- For validation, limit, date, field, or boundary criteria, the relevant rule/constraint must actually be exercised and an expected outcome asserted.
- If the generated tests only partially address the criterion, mark covered=false.
- Judge only coverage of this acceptance criterion; do not reward general test quality.
- Return ONLY valid JSON, no markdown, no prose.

Output schema:
{"covered": true | false, "reason": "one concise sentence explaining the concrete evidence or what is missing"}
"""

def evaluate_ac_coverage(
    us_id_value: str,
    cases: List[Dict[str, Any]],
    ac_blob: str,
    bulk_checkpoint_state: Optional[Dict[str, Any]] = None,
    bulk_checkpoint_path: Optional[str] = None,
    bulk_run_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    AC Coverage evaluation using LLM-as-a-Judge.

    During a bulk run, every successfully judged acceptance criterion is written to the
    on-disk checkpoint immediately. If the app stops, a resumed run reuses those saved
    judge results and calls the API only for acceptance criteria that are still missing
    or previously failed.
    """
    if not client:
        return {
            "overall_pct": None,
            "covered_count": None,
            "total_count": None,
            "details": [],
            "note": "LLM judge not available (missing API client)."
        }

    ac_lines = [l.strip() for l in ac_blob.splitlines() if l.strip()]
    if not ac_lines:
        return {
            "overall_pct": None,
            "covered_count": None,
            "total_count": None,
            "details": [],
            "note": "No acceptance criteria text provided for LLM judge."
        }

    # Build a compact readable representation of the test cases.
    tc_text_parts = []
    for tc in cases:
        parts = [f"[{tc.get('id','')}] {tc.get('title','')}"]
        for step in tc.get("steps", []) or []:
            if isinstance(step, dict):
                parts.append(f"  Step: {step.get('step','')}")
                parts.append(f"  Expected: {step.get('expected','')}")
        tc_text_parts.append("\n".join(parts))
    tc_text = "\n\n".join(tc_text_parts)

    judge_cache: Dict[str, Any] = {}
    if bulk_checkpoint_state is not None and bulk_run_key:
        run_state = bulk_checkpoint_state.setdefault("runs", {}).setdefault(bulk_run_key, {})
        ac_judge_state = run_state.setdefault("ac_judge", {})
        ac_judge_state["judge_version"] = AC_JUDGE_VERSION
        judge_cache = ac_judge_state.setdefault("details", {})

    details: List[Dict[str, Any]] = []
    covered_count = 0
    failed_count = 0

    for idx, ac_line in enumerate(ac_lines, start=1):
        ac_id = f"AC-{idx}"
        cached = judge_cache.get(ac_id) if judge_cache else None

        # Reuse only results produced by the CURRENT strict judge definition.
        # Older cached judgements are intentionally re-judged, but the generated
        # test cases themselves are reused, so no generation call is repeated.
        if (
            isinstance(cached, dict)
            and cached.get("status") == "complete"
            and cached.get("judge_version") == AC_JUDGE_VERSION
            and cached.get("ac_text") == ac_line
        ):
            covered = bool(cached.get("covered", False))
            reason = str(cached.get("reason", ""))
            detail = {
                "ac_id": ac_id,
                "ac_text": ac_line,
                "covered": covered,
                "reason": reason,
                "score": 1.0 if covered else 0.0,
            }
            details.append(detail)
            if covered:
                covered_count += 1
            continue

        payload = {
            "acceptance_criterion": ac_line,
            "generated_test_cases": tc_text,
        }
        try:
            resp = client.chat.completions.create(
                model=AC_JUDGE_MODEL,
                reasoning_effort=AC_JUDGE_REASONING_EFFORT,
                max_completion_tokens=AC_JUDGE_MAX_COMPLETION_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw, flags=re.S).strip()
            result = json.loads(raw)
            if "covered" not in result:
                raise ValueError("Judge response has no 'covered' field.")
            covered = bool(result.get("covered", False))
            reason = str(result.get("reason", "")).strip() or "No reason returned by judge."

            if judge_cache is not None:
                judge_cache[ac_id] = {
                    "status": "complete",
                    "judge_version": AC_JUDGE_VERSION,
                    "judge_model": AC_JUDGE_MODEL,
                    "ac_text": ac_line,
                    "covered": covered,
                    "reason": reason,
                }
                if bulk_checkpoint_state is not None and bulk_checkpoint_path:
                    _save_bulk_checkpoint(bulk_checkpoint_path, bulk_checkpoint_state)

            detail = {
                "ac_id": ac_id,
                "ac_text": ac_line,
                "covered": covered,
                "reason": reason,
                "score": 1.0 if covered else 0.0,
            }
            details.append(detail)
            if covered:
                covered_count += 1

        except Exception as e:
            failed_count += 1
            reason = f"Judge call failed: {e}"
            detail = {
                "ac_id": ac_id,
                "ac_text": ac_line,
                "covered": None,
                "reason": reason,
                "score": None,
            }
            details.append(detail)

            if judge_cache is not None:
                judge_cache[ac_id] = {
                    "status": "failed",
                    "judge_version": AC_JUDGE_VERSION,
                    "judge_model": AC_JUDGE_MODEL,
                    "ac_text": ac_line,
                    "covered": None,
                    "reason": reason,
                }
                if bulk_checkpoint_state is not None and bulk_checkpoint_path:
                    _save_bulk_checkpoint(bulk_checkpoint_path, bulk_checkpoint_state)

    total = len(ac_lines)
    # Never silently turn API failures into "not covered". Incomplete judge runs stay
    # incomplete and are retried on the next resume.
    overall_pct = None if failed_count else round((covered_count / total) * 100, 2)
    note = None
    if failed_count:
        note = (
            f"AC Coverage incomplete: {failed_count} judge call(s) failed. "
            "Successful AC judgements were checkpointed and will not be repeated; "
            "resume the bulk evaluation to retry only the failed ACs."
        )

    return {
        "overall_pct": overall_pct,
        "covered_count": covered_count if not failed_count else None,
        "total_count": total,
        "details": details,
        "note": note,
    }


# ======================= NAVIGATION EXTRACTION HELPERS =======================

def _ui_nodes() -> List[Dict[str, Any]]:
    if isinstance(UI_CONTEXT, dict):
        nodes = UI_CONTEXT.get("nodes", []) or []
        return [n for n in nodes if isinstance(n, dict) and n.get("id")]
    return []


def _node_ids() -> set:
    return {str(n.get("id")) for n in _ui_nodes()}


def _parent_map() -> Dict[str, Optional[str]]:
    return {str(n.get("id")): n.get("parent") for n in _ui_nodes()}


def _node_name_map() -> Dict[str, str]:
    return {str(n.get("id")): str(n.get("name", "")) for n in _ui_nodes()}


def _relationship_target_by_via() -> Dict[str, str]:
    rels = UI_CONTEXT.get("relationships", []) if isinstance(UI_CONTEXT, dict) else []
    mapping = {}
    for rel in rels or []:
        if not isinstance(rel, dict):
            continue
        via = rel.get("via")
        to = rel.get("to")
        if via and to:
            mapping[str(via)] = str(to)
    return mapping


def _relationship_records() -> List[Dict[str, Any]]:
    """Return valid UI transition records from ``ui_context.json``."""
    rels = UI_CONTEXT.get("relationships", []) if isinstance(UI_CONTEXT, dict) else []
    return [r for r in (rels or []) if isinstance(r, dict) and r.get("to")]


def _relationship_targets_for_step(
    explicit_node_id: str,
    step_text: str,
    expected_text: str,
) -> List[str]:
    """Infer only *directly reached* relationship targets for one generated step.

    This is intentionally narrower than the old path expansion:
    - no parent/ancestor chain is inserted;
    - a relationship target is added only when the model explicitly references the
      relationship's ``via`` node (or, for ``via: null``, its ``from`` node) AND
      the step actually performs an activating action such as click/select/open;
    - a passive verification such as "Verify Add Action Button is visible" does
      not count as opening the popup behind that button.

    This lets a step like "Open an existing SM using the SM ID Link" count the
    resulting ``SM Detail`` screen as reached, because that transition is explicitly
    defined in ``ui_context.json``. It does not complete missing parent paths for the
    model.
    """
    explicit = str(explicit_node_id or "").strip()
    if not explicit or explicit == "LOGIN":
        return []

    action = normalize_text(step_text or "")
    expected = normalize_text(expected_text or "")

    # Verbs that indicate that the referenced UI control/state is actually used to
    # trigger a transition. Merely checking/inspecting a control is deliberately not
    # enough.
    activation_patterns = [
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
    activates = any(re.search(p, action) for p in activation_patterns)

    name_map = _node_name_map()
    valid_ids = _node_ids()
    reached: List[str] = []

    for rel in _relationship_records():
        via = str(rel.get("via") or "").strip()
        source = str(rel.get("from") or "").strip()
        target = str(rel.get("to") or "").strip()
        if target not in valid_ids:
            continue

        # Normal case: the generated step explicitly references the clickable/
        # selectable ``via`` node. Some modeled transitions intentionally have no
        # via node; for those, the current/source node may be referenced instead.
        references_transition = (via and explicit == via) or (not via and source and explicit == source)
        if not references_transition:
            continue

        target_name = normalize_text(name_map.get(target, ""))
        target_named_in_expected = bool(target_name and target_name in expected)
        expected_transition_words = bool(re.search(
            r"\b(open|opens|opened|display|displayed|shown|show|appears|appear|redirect|redirected|navigate|navigated|load|loaded|return|returned)\b",
            expected,
        ))

        # Prefer the action itself as evidence. The expected-result fallback is useful
        # for model phrasing where the action is terse but the resulting screen/modal
        # is explicitly named.
        if activates or (target_named_in_expected and expected_transition_words):
            if target != explicit and target not in reached:
                reached.append(target)

    return reached


def _ancestor_chain(node_id: str) -> List[str]:
    """Returns ancestors from root to node, based on parent links in ui_context."""
    parents = _parent_map()
    valid_ids = _node_ids()
    chain = []
    current = node_id
    seen = set()
    while current and current in valid_ids and current not in seen:
        seen.add(current)
        chain.append(current)
        current = parents.get(current)
    return list(reversed(chain))


def _append_unique(path: List[str], node_id: Optional[str]):
    if node_id and node_id != "LOGIN" and node_id not in path:
        path.append(node_id)


def _append_chain(path: List[str], node_id: Optional[str]):
    if not node_id or node_id == "LOGIN":
        return
    chain = _ancestor_chain(str(node_id)) or [str(node_id)]
    for n in chain:
        _append_unique(path, n)


def _expand_via_node(node_id: str) -> List[str]:
    """If a node is a button/link that opens/navigates to a target, include the target too."""
    rel_map = _relationship_target_by_via()
    target = rel_map.get(str(node_id))
    if target and target != node_id:
        return [str(node_id), target]
    return [str(node_id)]


def _detect_module_scope(text: str) -> Optional[str]:
    """
    Returns a coarse module scope for text inference.
    Detects whether a text refers to the SM or TM module.
    """
    txt = normalize_text(text)

    sm_patterns = [
        r"\bstrategic meeting\b", r"\bstrategic meetings\b", r"\bsm\b",
        r"\bsm module\b", r"\bsm dashboard\b", r"\bsm detail\b",
        r"\bcreate sm\b", r"\bedit sm\b", r"\bdelete sm\b",
    ]
    tm_patterns = [
        r"\bteam meeting\b", r"\bteam meetings\b", r"\btm\b",
        r"\btm module\b", r"\btm dashboard\b", r"\btm detail\b",
        r"\bcreate tm\b", r"\bedit tm\b", r"\bdelete tm\b",
    ]

    # Backwards-compatible aliases only as fallback for old/manual inputs.
    old_sm_patterns = [r"\bmanager meeting\b", r"\bmanager meetings\b", r"\bmm\b", r"\bmm module\b"]
    old_tm_patterns = [r"\bagent meeting\b", r"\bagent meetings\b", r"\bam\b", r"\bam module\b"]

    is_sm = any(re.search(p, txt) for p in sm_patterns + old_sm_patterns)
    is_tm = any(re.search(p, txt) for p in tm_patterns + old_tm_patterns)

    if is_sm and not is_tm:
        return "SM"
    if is_tm and not is_sm:
        return "TM"
    return None


def _detect_function_scope(text: str) -> str:
    """Distinguishes meeting-level actions from action-level actions."""
    txt = normalize_text(text)
    if re.search(r"\baction\b|\bactions\b", txt):
        return "ACTION"
    return "MEETING"


def infer_nodes_from_step_text(step_text: str, expected_text: str) -> List[str]:
    """
    Conservative fallback inference of UI node IDs from text.

    The main evaluation signal should be explicit ui_node_id values generated
    with UI context. This fallback only maps very obvious names to the NEW
    simplified node IDs (SM/TM and neutral consoles).
    """
    text = normalize_text(f"{step_text} {expected_text}")
    found: List[str] = []
    valid_ids = _node_ids()

    def add(node_id: str):
        if node_id and node_id in valid_ids and node_id not in found:
            found.append(node_id)

    # Neutral workspaces
    if re.search(r"\boperations\b", text):
        add("CONSOLE-O")
    if re.search(r"\bcoordination\b", text):
        add("CONSOLE-C")
    if re.search(r"\bscheduling\b", text):
        add("CONSOLE-S")
    if re.search(r"\bperformance\b", text):
        add("CONSOLE-P")

    # Strategic Meeting / SM
    if re.search(r"\bstrategic meeting\b|\bsm\b", text):
        add("OPT-SM")
        if "dashboard" in text:
            add("SCR-SM-DASHBOARD")
        if "detail" in text or "details" in text:
            add("SCR-SM-DETAIL")
        if "list" in text and "action" not in text:
            add("COMP-SM-LIST")
        if "action list" in text or "list of actions" in text or "sm action list" in text:
            add("COMP-SM-ACTION-LIST")
        if "create" in text and ("popup" in text or "modal" in text or "opens" in text or "appears" in text):
            if "action" in text:
                add("MOD-SM-ACTION-CREATE")
            else:
                add("MOD-SM-CREATE")
        if "edit" in text and ("popup" in text or "modal" in text or "opens" in text or "appears" in text):
            if "action" in text:
                add("MOD-SM-ACTION-EDIT")
            else:
                add("MOD-SM-EDIT")
        if "delete" in text and ("popup" in text or "modal" in text or "confirmation" in text or "opens" in text or "appears" in text):
            if "action" in text:
                add("MOD-SM-ACTION-DELETE")
            else:
                add("MOD-SM-DELETE")

    # Team Meeting / TM
    if re.search(r"\bteam meeting\b|\btm\b", text):
        add("OPT-TM")
        if "dashboard" in text:
            add("SCR-TM-DASHBOARD")
        if "detail" in text or "details" in text:
            add("SCR-TM-DETAIL")
        if "list" in text and "action" not in text:
            add("COMP-TM-LIST")
        if "action list" in text or "list of actions" in text or "tm action list" in text:
            add("COMP-TM-ACTION-LIST")
        if "create" in text and ("popup" in text or "modal" in text or "opens" in text or "appears" in text):
            if "action" in text:
                add("MOD-TM-ACTION-CREATE")
            else:
                add("MOD-TM-CREATE")
        if "edit" in text and ("popup" in text or "modal" in text or "opens" in text or "appears" in text):
            if "action" in text:
                add("MOD-TM-ACTION-EDIT")
            else:
                add("MOD-TM-EDIT")
        if "delete" in text and ("popup" in text or "modal" in text or "confirmation" in text or "opens" in text or "appears" in text):
            if "action" in text:
                add("MOD-TM-ACTION-DELETE")
            else:
                add("MOD-TM-DELETE")

    # Other modules
    if "calendar" in text:
        add("OPT-CALENDAR")
        add("SCR-CALENDAR")
        if "search" in text:
            add("EL-CALENDAR-SEARCH-BTN")
        if "accept" in text:
            add("EL-CALENDAR-ACCEPT")
        if "decline" in text:
            add("EL-CALENDAR-DECLINE")
        if "cancel" in text:
            add("EL-CALENDAR-CANCEL")
        if "meeting" in text:
            add("EL-CALENDAR-MEETING")

    if "evaluate employees" in text or "evaluation page" in text:
        add("OPT-EVALUATE")
        if "dashboard" in text:
            add("SCR-EVALUATE-DASHBOARD")
        if "evaluation page" in text or "detail" in text:
            add("SCR-EVALUATE-DETAIL")

    if "my evaluations" in text or "my evaluation" in text:
        add("OPT-MY-EVAL")
        if "dashboard" in text:
            add("SCR-MY-EVAL-DASHBOARD")
        if "detail" in text or "details" in text:
            add("SCR-MY-EVAL-DETAIL")
        if "appeal" in text and ("popup" in text or "modal" in text or "opens" in text or "appears" in text):
            add("MOD-EVAL-APPEAL")

    return found


def extract_actual_nav_path(tc: Dict[str, Any], allow_text_inference: bool = False) -> List[str]:
    """Return the navigation path supported by the generated steps.

    Main-evaluation behavior uses a balanced rule:
    - explicit, valid ``ui_node_id`` values emitted by the model are counted;
    - the original step order is preserved;
    - parent/ancestor nodes are NEVER inserted automatically;
    - a direct relationship target may be counted when an explicit step actually
      activates the modeled transition (for example clicking an SM ID Link reaches
      SM Detail);
    - passive checks do not trigger relationship expansion;
    - text inference remains disabled for the main experiment.

    Consecutive duplicates are collapsed because several actions inside the same
    screen/modal may legitimately carry the same ``ui_node_id``. Re-visiting a node
    later in the path is still preserved.
    """
    path: List[str] = []
    valid_ids = _node_ids()

    def append_node(node_id: Optional[str]):
        node = str(node_id or "").strip()
        if not node or node == "LOGIN" or node not in valid_ids:
            return
        if not path or path[-1] != node:
            path.append(node)

    all_steps: List[Any] = []
    all_steps.extend(tc.get("navigation_steps", []) or [])
    all_steps.extend(tc.get("steps_only", []) or [])

    # In normalized outputs, tc["steps"] already contains navigation_steps +
    # steps_only. Use it only as a fallback so the same evidence is not counted twice.
    if not all_steps:
        all_steps.extend(tc.get("steps", []) or [])

    for s in all_steps:
        if isinstance(s, dict):
            step_text = s.get("step", "") or ""
            expected_text = s.get("expected", "") or ""
            explicit = s.get("ui_node_id")
        else:
            step_text = str(s)
            expected_text = ""
            explicit = None

        explicit_str = str(explicit or "").strip()
        if explicit_str and explicit_str != "LOGIN" and explicit_str in valid_ids:
            append_node(explicit_str)

            # Count only the immediate UI state reached by an explicitly activated
            # relationship. This is not ancestor completion: the target must be a
            # direct transition from the explicit node/source in ui_context.json.
            for target in _relationship_targets_for_step(
                explicit_str, step_text, expected_text
            ):
                append_node(target)

        elif allow_text_inference:
            for node in infer_nodes_from_step_text(step_text, expected_text):
                append_node(node)

    return path


def find_navigation_targets(us_id_value: str) -> Optional[Dict[str, Any]]:
    """Returns target-based navigation reference for a User Story."""
    if not isinstance(NAV_TARGETS, dict):
        return None
    direct = NAV_TARGETS.get(us_id_value.strip())
    if direct:
        return direct
    # Case-insensitive fallback
    for key, value in NAV_TARGETS.items():
        if str(key).strip().lower() == us_id_value.strip().lower():
            return value
    return None


def _norm_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, list):
        return [str(v) for v in values if str(v).strip()]
    return [str(values)]


def _text_contains_any(text: str, keywords: List[str]) -> bool:
    return any(normalize_text(k) in text for k in keywords if normalize_text(k))


def _keyword_score(text: str, keywords: List[str]) -> int:
    return sum(1 for k in keywords if normalize_text(k) and normalize_text(k) in text)


def _target_required_nodes(target: Any) -> List[str]:
    """Return required node IDs from all supported target formats.

    Supported formats:
    1) New simplest format per US:
       {"title": "Create SM", "targets": ["CONSOLE-O", "OPT-SM", ...]}
    2) Minimal compatible format:
       {"label": "...", "required_nodes": ["CONSOLE-O", ...]}
    3) Legacy format with target_nodes.
    """
    if not target:
        return []
    if isinstance(target, list):
        return [str(v) for v in target if str(v).strip()]
    if isinstance(target, str):
        return [target]
    if isinstance(target, dict):
        return _norm_list(target.get("required_nodes") or target.get("target_nodes") or target.get("targets"))
    return []


def _target_label(target: Any, ref: Optional[Dict[str, Any]] = None) -> str:
    if isinstance(target, dict):
        return str(target.get("label") or target.get("title") or (ref or {}).get("title") or "Navigation target")
    return str((ref or {}).get("title") or "Navigation target")


def _target_forbidden_nodes(target: Any) -> List[str]:
    if isinstance(target, dict):
        return _norm_list(target.get("forbidden_nodes"))
    return []


def _target_access_denial_ok(target: Any) -> bool:
    return bool(isinstance(target, dict) and target.get("access_denial_ok"))


def _select_best_navigation_target(tc: Dict[str, Any], ref: Dict[str, Any]) -> Any:
    """Selects a navigation target and supports simplified target files.

    New recommended format uses one target set per User Story:
      "US-6": {"title":"Create Action for SM",
               "targets":["CONSOLE-O","OPT-SM","SCR-SM-DETAIL","MOD-SM-ACTION-CREATE"]}

    The function still supports the old list-of-dicts format for compatibility.
    """
    targets = ref.get("targets", []) if isinstance(ref, dict) else []
    if not targets:
        return {}

    # New simple format: targets is directly a list of node ID strings.
    if isinstance(targets, list) and all(isinstance(x, str) for x in targets):
        return {"label": ref.get("title", "Navigation target"), "required_nodes": targets}

    # Also support list of node-id lists by using the first set.
    if isinstance(targets, list) and all(isinstance(x, list) for x in targets):
        first = targets[0] if targets else []
        return {"label": ref.get("title", "Navigation target"), "required_nodes": first}

    # Old format: targets is a list of dictionaries with labels/keywords.
    if isinstance(targets, list) and all(isinstance(x, dict) for x in targets):
        txt = testcase_full_text(tc)
        default_label = str(ref.get("default_target", "")).strip().lower()

        scored = []
        for idx, target in enumerate(targets):
            keywords = _norm_list(target.get("keywords"))
            score = _keyword_score(txt, keywords)
            if default_label and str(target.get("label", "")).strip().lower() == default_label:
                score += 0.1
            scored.append((score, idx, target))

        scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        best_score, _, best_target = scored[0]

        if best_score <= 0.1:
            for target in targets:
                if default_label and str(target.get("label", "")).strip().lower() == default_label:
                    return target
            return targets[0]
        return best_target

    return {}


def _contains_denial_language(tc: Dict[str, Any]) -> bool:
    txt = testcase_full_text(tc)
    denial_patterns = [
        "not visible", "not available", "not accessible", "cannot", "can not",
        "no permission", "permission denied", "access denied", "denied", "disabled",
        "not allowed", "blocked", "unavailable", "not editable", "does not allow",
        "prevents", "rejected", "validation"
    ]
    return any(p in txt for p in denial_patterns)


def navigation_negative_mode(tc: Dict[str, Any]) -> str:
    """Classify test cases for navigation evaluation.

    Returns:
      - "none": positive/boundary test; evaluate against required_per_testcase normally.
      - "no_access": role cannot access the module at all (e.g. Agent cannot view SM).
        These are NOT skipped — instead they are evaluated for denial correctness:
        correct if the test case contains explicit denial/restriction language,
        incorrect if it does not. This keeps all test cases in the metric.
      - "base_only": role reaches the base area but a create/edit/delete action is
        denied. Evaluated against required_per_testcase only (not required_across_story).
    """
    txt = testcase_full_text(tc)
    tc_type = normalize_text(str(tc.get("type", "")))
    negative_type = "negative" in tc_type

    has_manager_or_agent = any(role in txt for role in ["manager", "agent"])
    has_permission_language = any(p in txt for p in [
        "permission", "permissions", "access", "role", "insufficient permissions",
        "not allowed", "denied", "blocked", "disabled", "not actionable",
        "not available", "not visible", "cannot be opened", "cannot be accessed",
        "can not be opened", "can not be accessed"
    ])

    no_view_patterns = [
        "cannot view", "can not view", "not view", "cannot see", "can not see",
        "not see", "cannot access", "can not access", "not access",
        "cannot be accessed", "can not be accessed", "not accessible",
        "cannot be opened", "can not be opened", "not visible"
    ]
    mentions_module_or_dashboard = any(p in txt for p in [
        "module", "dashboard", "strategic meeting", "team meeting", "sm module", "tm module"
    ])
    if has_manager_or_agent and mentions_module_or_dashboard and any(p in txt for p in no_view_patterns):
        return "no_access"

    action_denial_patterns = [
        "cannot create", "can not create", "not create", "cannot initiate",
        "can not initiate", "cannot edit", "can not edit", "not edit",
        "cannot delete", "can not delete", "not delete", "creation is denied",
        "action is denied", "prevents opening", "no create", "no edit", "no delete"
    ]
    mentions_restricted_action = any(p in txt for p in action_denial_patterns)
    mentions_control_denial = any(p in txt for p in [
        "button is not available", "button is disabled", "control is not available",
        "control is disabled", "not actionable", "access is denied", "action is blocked",
        "blocked due to insufficient permissions", "denies the action"
    ])

    if (negative_type or has_permission_language) and has_manager_or_agent and (mentions_restricted_action or mentions_control_denial):
        return "base_only"

    return "none"


def is_negative_permission_or_access_test(tc: Dict[str, Any]) -> bool:
    """Backward-compatible boolean helper used by older code paths."""
    return navigation_negative_mode(tc) in {"base_only", "no_access"}


def _invalid_explicit_ui_node_ids(tc: Dict[str, Any]) -> List[str]:
    """Return explicit ui_node_id values that do not exist in ui_context.json.

    Navigation Path Correctness deliberately does NOT validate every direct UI
    transition. Repeated interaction on the same screen (for example search ->
    edit search -> search again) is valid and should not be rejected merely
    because two consecutive emitted nodes are not parent/child neighbours.

    Unknown/invented ui_node_id values are still treated as invalid evidence.
    """
    valid_ids = _node_ids()
    invalid: List[str] = []

    all_steps: List[Any] = []
    all_steps.extend(tc.get("navigation_steps", []) or [])
    all_steps.extend(tc.get("steps_only", []) or [])
    if not all_steps:
        all_steps.extend(tc.get("steps", []) or [])

    for s in all_steps:
        if not isinstance(s, dict):
            continue
        explicit = s.get("ui_node_id")
        if explicit in (None, "", "LOGIN"):
            continue
        node_id = str(explicit).strip()
        if node_id and node_id not in valid_ids and node_id not in invalid:
            invalid.append(node_id)

    return invalid



def _is_ancestor_node(ancestor: str, node: str) -> bool:
    """Return True when ``ancestor`` is a parent/ancestor of ``node`` in ui_context."""
    parents = _parent_map()
    current = str(node or "").strip()
    target = str(ancestor or "").strip()
    seen = set()

    while current and current not in seen:
        seen.add(current)
        current = str(parents.get(current) or "").strip()
        if current == target:
            return True
    return False


def _is_explicit_relationship_transition(source: str, target: str) -> bool:
    """Return True when ui_context.relationships explicitly permits source -> target.

    A relationship may be represented as from -> via -> to.  Because optional
    intermediate UI nodes are allowed to be omitted for Navigation Path
    Correctness, from -> to is accepted as well.
    """
    source = str(source or "").strip()
    target = str(target or "").strip()

    for rel in _relationship_records():
        rel_from = str(rel.get("from") or "").strip()
        rel_via = str(rel.get("via") or "").strip()
        rel_to = str(rel.get("to") or "").strip()

        if rel_from and rel_via and source == rel_from and target == rel_via:
            return True
        if rel_via and rel_to and source == rel_via and target == rel_to:
            return True
        if rel_from and rel_to and source == rel_from and target == rel_to:
            return True

    return False


def _ui_transition_is_valid(source: str, target: str) -> bool:
    """Validate one emitted UI-path transition against ui_context.

    Allowed transitions:
    - same node (defensive; consecutive duplicates are normally collapsed),
    - ancestor <-> descendant (optional intermediate hierarchy nodes may be skipped),
    - sibling <-> sibling when both nodes have the same parent,
    - an explicit relationship transition from ui_context.json.

    This lets a test interact repeatedly with controls inside the same UI branch
    (for example Search Bar <-> Search Button) without treating that as an
    invalid navigation path, while still rejecting jumps to unrelated branches.
    """
    source = str(source or "").strip()
    target = str(target or "").strip()
    valid_ids = _node_ids()

    if not source or not target:
        return True
    if source == target:
        return True
    if source not in valid_ids or target not in valid_ids:
        return False

    # Moving down or back up the same hierarchy branch is valid. Intermediate
    # non-required nodes may be omitted from the generated path.
    if _is_ancestor_node(source, target) or _is_ancestor_node(target, source):
        return True

    # Two controls/components under the exact same parent belong to the same UI
    # context and may be used in either order.
    parents = _parent_map()
    source_parent = str(parents.get(source) or "").strip()
    target_parent = str(parents.get(target) or "").strip()
    if source_parent and source_parent == target_parent:
        return True

    if _is_explicit_relationship_transition(source, target):
        return True

    return False


def _invalid_ui_path_transitions(path: List[str]) -> List[Dict[str, str]]:
    """Return invalid consecutive transitions in the generated UI path."""
    invalid: List[Dict[str, str]] = []
    for source, target in zip(path, path[1:]):
        if not _ui_transition_is_valid(source, target):
            invalid.append({"from": source, "to": target})
    return invalid


def evaluate_navigation_correctness(us_id_value: str, cases: List[Dict[str, Any]], story: str = "") -> Dict[str, Any]:
    """Evaluate Navigation Path Correctness from the required base path.

    For the current two-level navigation target format, a positive/evaluable
    test case is correct when:

    1. every node in ``required_per_testcase`` occurs in the generated path;
    2. those required nodes occur in the defined order; and
    3. the model did not emit an unknown/invented ``ui_node_id``.

    Additional known UI nodes may occur before, between, or after the required
    nodes and may be repeated. They are not checked as direct transitions for
    this metric. This intentionally keeps Navigation Path Correctness focused on
    the mandatory base path and avoids false negatives caused by legitimate
    repeated interaction inside the same screen or modal.

    ``required_across_story`` does not contribute points to this metric. Those
    nodes are evaluated separately under Target Node Coverage.

    Formula:
        correct evaluable test cases / all evaluable test cases * 100
    """
    ref = find_navigation_targets(us_id_value)
    if not ref:
        return {
            "correctness_pct": None,
            "correct_count": None,
            "evaluated_count": None,
            "skipped_count": 0,
            "details": [],
            "note": f"No navigation targets found for {us_id_value}"
        }

    module_nodes = _norm_list(ref.get("module_nodes")) if isinstance(ref, dict) else []

    required_per_testcase = _norm_list(ref.get("required_per_testcase")) if isinstance(ref, dict) else []
    required_across_story = _norm_list(ref.get("required_across_story")) if isinstance(ref, dict) else []
    uses_two_level_format = bool(required_per_testcase or required_across_story)

    # Older target formats remain supported for compatibility.
    targets = ref.get("targets", []) if isinstance(ref, dict) else []

    if not uses_two_level_format and not targets:
        return {
            "correctness_pct": None,
            "correct_count": None,
            "evaluated_count": None,
            "skipped_count": 0,
            "details": [],
            "note": f"No target definitions found for {us_id_value}"
        }

    evaluated_cases = 0
    correct_cases = 0
    skipped_cases = 0
    details = []

    for tc in cases:
        actual = extract_actual_nav_path(tc, allow_text_inference=False)
        invalid_ui_node_ids = _invalid_explicit_ui_node_ids(tc)
        neg_mode = navigation_negative_mode(tc)

        if uses_two_level_format:
            # A real no-access permission test intentionally does not navigate to
            # the feature. Role/access correctness is measured elsewhere, so it
            # is excluded from this path metric.
            if neg_mode == "no_access":
                skipped_cases += 1
                details.append({
                    "tc_id": tc.get("id", ""),
                    "actual": actual,
                    "expected": required_per_testcase,
                    "selected_target": str(ref.get("title") or "Navigation target"),
                    "module_nodes": module_nodes,
                    "can_evaluate": False,
                    "is_correct": False,
                    "module_ok": False,
                    "missing_nodes": [],
                    "forbidden_nodes": [],
                    "forbidden_hit": False,
                    "denial_ok": _contains_denial_language(tc),
                    "order_ok": False,
                    "ui_path_ok": False,
                    "invalid_transitions": [],
                    "invalid_ui_node_ids": invalid_ui_node_ids,
                    "end_node": actual[-1] if actual else None,
                    "match_score": 0.0,
                    "skip_reason": "No-access permission test: no path to the feature is expected."
                })
                continue

            required_nodes = required_per_testcase
            selected_target = str(ref.get("title") or "Navigation target")
            if neg_mode == "base_only":
                selected_target += " — base navigation"
            forbidden_nodes: List[str] = []
            target = {"label": selected_target, "required_nodes": required_nodes}

        else:
            # Compatibility behavior for old navigation target definitions.
            if neg_mode in {"no_access", "base_only"}:
                skipped_cases += 1
                details.append({
                    "tc_id": tc.get("id", ""),
                    "actual": actual,
                    "expected": [],
                    "selected_target": "skipped_negative_permission_old_target_format",
                    "module_nodes": module_nodes,
                    "can_evaluate": False,
                    "is_correct": False,
                    "module_ok": False,
                    "missing_nodes": [],
                    "forbidden_nodes": [],
                    "forbidden_hit": False,
                    "denial_ok": _contains_denial_language(tc),
                    "order_ok": False,
                    "ui_path_ok": False,
                    "invalid_transitions": [],
                    "invalid_ui_node_ids": invalid_ui_node_ids,
                    "end_node": actual[-1] if actual else None,
                    "match_score": 0.0,
                    "skip_reason": "Negative permission/access test with legacy target format."
                })
                continue

            target = _select_best_navigation_target(tc, ref)
            required_nodes = _target_required_nodes(target)
            forbidden_nodes = _target_forbidden_nodes(target)
            selected_target = _target_label(target, ref)

        # A defined reference makes the case evaluable even when the model emitted
        # no ui_node_id. Missing required evidence then counts as incorrect.
        can_evaluate = bool(required_nodes)

        module_ok = True if not module_nodes else any(m in actual for m in module_nodes)
        required_present_ok = all(node in actual for node in required_nodes)
        required_order_ok = _is_ordered_subsequence(required_nodes, actual)
        required_ok = required_present_ok and required_order_ok

        known_ids_ok = len(invalid_ui_node_ids) == 0
        # Navigation Path Correctness intentionally does not validate every
        # consecutive transition. Additional/repeated known UI nodes are allowed;
        # only the required base path and known node IDs are evaluated here.
        invalid_transitions: List[Dict[str, str]] = []
        ui_path_ok = known_ids_ok

        forbidden_hit = any(node in actual for node in forbidden_nodes)
        denial_ok = _target_access_denial_ok(target) and _contains_denial_language(tc)
        forbidden_ok = (not forbidden_hit) or denial_ok

        is_correct = False
        if can_evaluate:
            evaluated_cases += 1
            is_correct = bool(module_ok and required_ok and ui_path_ok and forbidden_ok)
            if is_correct:
                correct_cases += 1

        missing_nodes = [node for node in required_nodes if node not in actual]

        details.append({
            "tc_id": tc.get("id", ""),
            "actual": actual,
            "expected": required_nodes,
            "selected_target": selected_target,
            "module_nodes": module_nodes,
            "can_evaluate": can_evaluate,
            "is_correct": is_correct,
            "module_ok": module_ok,
            "missing_nodes": missing_nodes,
            "forbidden_nodes": forbidden_nodes,
            "forbidden_hit": forbidden_hit,
            "denial_ok": denial_ok,
            "order_ok": required_order_ok,
            "ui_path_ok": ui_path_ok,
            "invalid_transitions": invalid_transitions,
            "invalid_ui_node_ids": invalid_ui_node_ids,
            "end_node": actual[-1] if actual else None,
            "match_score": round((len(required_nodes) - len(missing_nodes)) / len(required_nodes), 2) if required_nodes else 0.0,
            "skip_reason": "" if can_evaluate else "No per-testcase navigation path is defined."
        })

    correctness_pct = (
        round((correct_cases / evaluated_cases) * 100, 2)
        if evaluated_cases else None
    )

    if evaluated_cases:
        note = None
    elif skipped_cases:
        note = "No evaluable navigation paths remained after excluding no-access permission tests."
    else:
        note = "No evaluable navigation test cases found."

    return {
        "correctness_pct": correctness_pct,
        "correct_count": correct_cases,
        "evaluated_count": evaluated_cases,
        "testcase_correct_count": correct_cases,
        "testcase_evaluated_count": evaluated_cases,
        "story_target_correct_count": 0,
        "story_target_total_count": 0,
        "skipped_count": skipped_cases,
        "details": details,
        "note": note
    }


def extract_required_roles(story: str, ac_blob: str) -> List[str]:
    """
    Extracts required roles from actor/permission wording only.

    Important: module names such as "Strategic Meeting" or "Team Meeting"
    must not be counted as Manager/Agent roles.
    """
    text = normalize_text(story + " " + ac_blob)
    found = set()

    for role in ROLE_WORDS:
        patterns = [
            rf"\bas\s+(?:a|an)?\s*{role}\b",
            rf"\buser\s+with\s+the\s+role\s+{role}\b",
            rf"\b{role}\s+can\b",
            rf"\b{role}s\s+can\b",
            rf"\b{role}\s+cannot\b",
            rf"\b{role}s\s+cannot\b",
            rf"\b{role}\s+can\s+not\b",
            rf"\b{role}s\s+can\s+not\b",
            rf"\bonly\s+(?:a\s+|an\s+)?(?:user\s+with\s+the\s+role\s+)?{role}\b",
            rf"\blogged\s+in\s+{role}\b",
        ]
        if any(re.search(pat, text) for pat in patterns):
            found.add(role)

    return sorted(found)

def step_implies_role(step_text: str, role: str) -> bool:
    """Return True when THIS ONE generated action step explicitly logs in with ``role``.

    Flexible wording between the login phrase and the role is allowed, e.g.:
    - "Log in as Agent"
    - "Log in as an Agent"
    - "Log in as the assigned Agent"
    - "Login as a user with the role Agent"

    The wildcard is deliberately bounded: it may consume arbitrary wording inside
    this single step, but it may NOT jump across another known role name first.
    Therefore "Log in as Manager and review data for Agent" counts only Manager,
    not Agent. Expected-result text and other test steps are never included.
    """
    text = normalize_text(step_text)
    if not text:
        return False

    wanted_role = re.escape(str(role).lower())
    all_roles = "|".join(re.escape(r.lower()) for r in ROLE_WORDS)

    pattern = re.compile(
        rf"\b(?:log\s*in|login|logged\s*in|sign\s*in|signed\s*in)\s+"
        rf"(?:as|with)\s+"
        rf"(?:(?!\b(?:{all_roles})\b).)*?"
        rf"\b{wanted_role}\b",
        flags=re.IGNORECASE,
    )
    return bool(pattern.search(text))


def extract_generated_roles(cases: List[Dict[str, Any]]) -> List[str]:
    found = set()

    for tc in cases:
        for s in tc.get("steps", []) or []:
            if not isinstance(s, dict):
                continue

            # Intentionally inspect ONLY the action text of this single step.
            # Do not concatenate expected-result text or neighboring steps.
            step_text = str(s.get("step", ""))

            for role in ROLE_WORDS:
                if step_implies_role(step_text, role):
                    found.add(role)

    return sorted(found)

def evaluate_role_coverage(story: str, ac_blob: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    required = extract_required_roles(story, ac_blob)
    generated = extract_generated_roles(cases)
    covered = sorted(list(set(required) & set(generated)))
    missing = sorted(list(set(required) - set(generated)))

    pct = round((len(covered) / len(required)) * 100, 2) if required else None
    return {
        "overall_pct": pct,
        "covered_count": len(covered),
        "total_count": len(required),
        "required_roles": required,
        "generated_roles": generated,
        "missing_roles": missing
    }



def _is_ordered_subsequence(expected: List[str], actual: List[str]) -> bool:
    """True if all expected node IDs appear in actual in the same order."""
    if not expected:
        return True
    pos = 0
    for node in actual:
        if pos < len(expected) and node == expected[pos]:
            pos += 1
    return pos == len(expected)


def _navigation_path_not_evaluated_without_ui() -> Dict[str, Any]:
    return {
        "correctness_pct": None,
        "correct_count": None,
        "evaluated_count": None,
        "skipped_count": None,
        "details": [],
        "note": (
            "Navigation Path Correctness is only evaluated for outputs generated with UI context, "
            "because only those outputs are expected to contain explicit ui_node_id paths. "
            "Outputs without UI context contain natural-language navigation only, which is not reliable enough "
            "for automated path validation against ui_context.json."
        )
    }


def _target_node_not_evaluated_without_ui() -> Dict[str, Any]:
    return {
        "coverage_pct": None,
        "covered_count": None,
        "total_count": None,
        "actual_nodes": [],
        "expected_nodes": [],
        "missing_nodes": [],
        "details": [],
        "note": (
            "Target Node Coverage is only evaluated for outputs generated with UI context. "
            "Without UI context, the LLM does not produce reliable ui_node_id values; mapping natural-language "
            "steps to technical UI nodes would require fragile alias rules and could distort the comparison."
        ),
    }


def _target_nodes_from_ref(ref: Dict[str, Any]) -> List[str]:
    """Return the story-wide feature target nodes for Target Node Coverage.

    In the current two-level navigation target format the two node groups have
    deliberately separate purposes:

    - ``required_per_testcase`` defines the mandatory base navigation path and
      is evaluated only by Navigation Path Correctness.
    - ``required_across_story`` defines feature-specific target nodes that
      should be reached at least once somewhere in the generated test-case set
      and is evaluated by Target Node Coverage.

    Keeping the two lists separate prevents the same missing base-path node from
    lowering both navigation metrics.
    """
    if not isinstance(ref, dict):
        return []

    nodes: List[str] = []

    def add_many(values: List[str]):
        for node in values:
            node = str(node).strip()
            if node and node not in nodes:
                nodes.append(node)

    # Preferred current two-level format: Target Node Coverage measures only
    # the story-wide feature targets. required_per_testcase is handled by
    # Navigation Path Correctness and must not contribute here.
    across_story = _norm_list(ref.get("required_across_story"))
    if across_story:
        add_many(across_story)
        return nodes

    # Backward compatibility for older target formats that do not yet provide
    # required_across_story.
    targets = ref.get("targets", [])
    if isinstance(targets, list):
        if all(isinstance(x, str) for x in targets):
            add_many([str(x) for x in targets])
        elif all(isinstance(x, list) for x in targets):
            for group in targets:
                add_many([str(x) for x in group])
        elif all(isinstance(x, dict) for x in targets):
            for target in targets:
                add_many(_target_required_nodes(target))

    return nodes


def _extract_node_union_from_cases(cases: List[Dict[str, Any]], allow_text_inference: bool) -> List[str]:
    """Collects all UI nodes that appear in generated test cases."""
    union: List[str] = []
    for tc in cases:
        # Avoid counting denied-access tests as if they really reached the target.
        if navigation_negative_mode(tc) != "none":
            continue
        actual = extract_actual_nav_path(tc, allow_text_inference=allow_text_inference)
        for node in actual:
            if node not in union:
                union.append(node)
    return union


def evaluate_target_node_coverage(
    us_id_value: str,
    cases: List[Dict[str, Any]],
    allow_text_inference: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate whether all story-wide feature target nodes are reached somewhere
    in the generated output.

    In the current navigation_targets.json format this metric evaluates only
    ``required_across_story``. The mandatory base path in
    ``required_per_testcase`` is evaluated separately by Navigation Path
    Correctness, so the same base-path error is not counted twice.

    This metric is calculated only for the WITH-UI-CONTEXT variant. Explicit
    valid ``ui_node_id`` values are used as evidence. In addition, the immediate
    target of a modeled ui_context relationship may count when the generated
    step explicitly activates that relationship (for example clicking an ID
    link and thereby reaching its detail screen). Parent/ancestor completion and
    free-text inference remain disabled for the main experiment.

    Important: this checks whether the feature target nodes are reached. It does
    NOT prove that the mandatory base navigation path is correct. That is handled
    separately by Navigation Path Correctness.
    """
    ref = find_navigation_targets(us_id_value)
    if not ref:
        return {
            "coverage_pct": None,
            "covered_count": None,
            "total_count": None,
            "actual_nodes": [],
            "expected_nodes": [],
            "missing_nodes": [],
            "details": [],
            "note": f"No target nodes found for {us_id_value}"
        }

    expected_nodes = _target_nodes_from_ref(ref)
    if not expected_nodes:
        return {
            "coverage_pct": None,
            "covered_count": None,
            "total_count": None,
            "actual_nodes": [],
            "expected_nodes": [],
            "missing_nodes": [],
            "details": [],
            "note": f"No required target node definitions found for {us_id_value}"
        }

    actual_nodes = _extract_node_union_from_cases(cases, allow_text_inference=allow_text_inference)
    covered_nodes = [node for node in expected_nodes if node in actual_nodes]
    missing_nodes = [node for node in expected_nodes if node not in actual_nodes]
    pct = round((len(covered_nodes) / len(expected_nodes)) * 100, 2) if expected_nodes else None

    name_map = _node_name_map()
    details = [
        {
            "node_id": node,
            "node_name": name_map.get(node, node),
            "covered": node in covered_nodes,
        }
        for node in expected_nodes
    ]

    return {
        "coverage_pct": pct,
        "covered_count": len(covered_nodes),
        "total_count": len(expected_nodes),
        "actual_nodes": actual_nodes,
        "expected_nodes": expected_nodes,
        "missing_nodes": missing_nodes,
        "details": details,
        "note": None,
    }
def _navigation_not_evaluated_without_ui() -> Dict[str, Any]:
    # Backward-compatible alias; the UI now labels this metric as Navigation Path Correctness.
    return _navigation_path_not_evaluated_without_ui()


def evaluate_all(
    us_id_value: str,
    story: str,
    ac_blob: str,
    cases: List[Dict[str, Any]],
    use_ui_context: bool = True,
    bulk_checkpoint_state: Optional[Dict[str, Any]] = None,
    bulk_checkpoint_path: Optional[str] = None,
    bulk_run_key: Optional[str] = None,
) -> Dict[str, Any]:
    # AC Coverage is evaluated semantically with LLM-as-a-Judge for both variants.
    ac_coverage = evaluate_ac_coverage(
        us_id_value,
        cases,
        ac_blob,
        bulk_checkpoint_state=bulk_checkpoint_state,
        bulk_checkpoint_path=bulk_checkpoint_path,
        bulk_run_key=bulk_run_key,
    )

    # Target Node Coverage is calculated only for the with-UI-context variant.
    target_node = (
        evaluate_target_node_coverage(
            us_id_value=us_id_value,
            cases=cases,
            allow_text_inference=False,
        )
        if use_ui_context
        else _target_node_not_evaluated_without_ui()
    )

    # Navigation Path Correctness is also calculated only for the with-UI-context variant.
    navigation_path = (
        evaluate_navigation_correctness(us_id_value, cases, story)
        if use_ui_context
        else _navigation_path_not_evaluated_without_ui()
    )

    return {
        "ac": ac_coverage,
        "target_node": target_node,
        "navigation_path": navigation_path,
        # Backward-compatible alias for older PDF sections.
        "navigation": navigation_path,
        "role": evaluate_role_coverage(story, ac_blob, cases),
    }





# ======================= SINGLE EXPORT HELPERS =======================
def normalize_us_lookup_value(value: str) -> str:
    """Accepts values like '1', '01', 'US-1' and returns 'US-1'."""
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    m = re.search(r"(\d+)", raw)
    if not m:
        return raw
    return f"US-{int(m.group(1))}"


def find_userstory_by_id(userstories: List[Dict[str, Any]], lookup_value: str) -> Optional[Dict[str, Any]]:
    wanted = normalize_us_lookup_value(lookup_value)
    for item in userstories:
        if normalize_us_lookup_value(item.get("id", "")) == wanted:
            return item
    return None


# ======================= BULK EVALUATION HELPERS =======================
def load_bulk_userstories(source: Any) -> List[Dict[str, Any]]:
    """
    Loads multiple user stories from either a path or an uploaded JSON file.

    Expected JSON format:
    [
      {
        "id": "US-1",
        "title": "Create SM",
        "story": "As a ...",
        "acceptance_criteria": ["AC 1", "AC 2"]
      }
    ]
    """
    try:
        if isinstance(source, str):
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.load(source)
    except Exception as e:
        raise ValueError(f"Could not read bulk user stories JSON: {e}")

    if not isinstance(data, list):
        raise ValueError("Bulk user stories JSON must contain a list of user stories.")

    cleaned = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {idx} is not a JSON object.")

        us_id_bulk = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        story = str(item.get("story", "")).strip()
        acs = item.get("acceptance_criteria", [])

        if not us_id_bulk:
            raise ValueError(f"Entry {idx} is missing 'id'.")
        if not story:
            raise ValueError(f"Entry {idx} is missing 'story'.")
        if not isinstance(acs, list) or not acs:
            raise ValueError(f"Entry {idx} must contain a non-empty list 'acceptance_criteria'.")

        ac_blob = "\n".join(str(ac).strip() for ac in acs if str(ac).strip())
        if not ac_blob:
            raise ValueError(f"Entry {idx} has no usable acceptance criteria.")

        cleaned.append({
            "id": us_id_bulk,
            "title": title,
            "story": story,
            "ac_blob": ac_blob,
            "acceptance_criteria_count": len([ac for ac in acs if str(ac).strip()])
        })

    return cleaned


BULK_CHECKPOINT_VERSION = 1
BULK_CHECKPOINT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".bulk_checkpoints",
)


def _bulk_checkpoint_fingerprint(userstories: List[Dict[str, Any]], repetitions: int) -> str:
    """Stable ID so the same dataset + repetition count resumes the same run."""
    payload = {
        "version": BULK_CHECKPOINT_VERSION,
        "repetitions": int(repetitions),
        "userstories": userstories,
        "generation_model": GENERATOR_MODEL,
        "judge_model": AC_JUDGE_MODEL,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _bulk_checkpoint_path(userstories: List[Dict[str, Any]], repetitions: int) -> str:
    fp = _bulk_checkpoint_fingerprint(userstories, repetitions)
    return os.path.join(BULK_CHECKPOINT_DIR, f"bulk_{fp}.json")


def _new_bulk_checkpoint(userstories: List[Dict[str, Any]], repetitions: int) -> Dict[str, Any]:
    return {
        "checkpoint_version": BULK_CHECKPOINT_VERSION,
        "fingerprint": _bulk_checkpoint_fingerprint(userstories, repetitions),
        "repetitions": int(repetitions),
        "total_runs": len(userstories) * int(repetitions) * 2,
        "runs": {},
    }


def _load_bulk_checkpoint(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("checkpoint_version") != BULK_CHECKPOINT_VERSION:
            return None
        data.setdefault("runs", {})
        return data
    except Exception:
        # Keep a broken file for inspection instead of overwriting it silently.
        return None


def _save_bulk_checkpoint(path: str, state: Dict[str, Any]) -> None:
    """Atomic, fsync-backed save so a crash does not leave a half-written checkpoint."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _delete_bulk_checkpoint(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        os.remove(path)


def _bulk_checkpoint_stats(state: Optional[Dict[str, Any]]) -> Dict[str, int]:
    runs = (state or {}).get("runs", {}) if isinstance(state, dict) else {}
    completed = 0
    generated = 0
    judge_done = 0
    judge_failed = 0
    for run in runs.values():
        if not isinstance(run, dict):
            continue
        if run.get("generation_complete"):
            generated += 1
        if run.get("complete"):
            completed += 1
        details = run.get("ac_judge", {}).get("details", {})
        if isinstance(details, dict):
            for d in details.values():
                if isinstance(d, dict) and d.get("status") == "complete":
                    judge_done += 1
                elif isinstance(d, dict) and d.get("status") == "failed":
                    judge_failed += 1
    return {
        "completed": completed,
        "generated": generated,
        "judge_done": judge_done,
        "judge_failed": judge_failed,
    }


def _generation_failure_reason(cases: List[Dict[str, Any]], open_questions: List[str]) -> str:
    """Return a technical generation failure reason that must not be scored as test quality."""
    notes = [str(q).strip() for q in (open_questions or [])]
    lowered = [q.lower() for q in notes]

    for original, low in zip(notes, lowered):
        if low.startswith("openai call failed:"):
            return original
        if "model response was not valid json" in low:
            return "Model response was not valid JSON."
        if "openai client not initialized" in low:
            return original

    # An empty, valid JSON test_cases list is not automatically classified as a technical failure.
    # It remains a model output and can be evaluated as such.
    return ""


def _metric_or_none(evaluation: Dict[str, Any], section: str, key: str) -> Optional[float]:
    try:
        value = evaluation.get(section, {}).get(key)
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _overall_score(ac_pct: Optional[float], role_pct: Optional[float], target_pct: Optional[float], nav_path_pct: Optional[float]) -> Optional[float]:
    """
    Simple combined score for a run.
    It averages all available metric percentages.

    The score averages all available metric percentages.
    - Without UI context: AC Coverage + Role Coverage.
    - With UI context: AC Coverage + Role Coverage + Target Node Coverage + Navigation Path Correctness.

    Target/Navigation metrics are intentionally N/A without UI context because that variant does not
    produce reliable ui_node_id values for automated node/path validation.
    """
    values = [v for v in [ac_pct, role_pct, target_pct, nav_path_pct] if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def run_bulk_evaluation(userstories: List[Dict[str, Any]], repetitions: int) -> pd.DataFrame:
    """
    Crash-safe bulk evaluation.

    Cost-protection behavior:
    - every finished generation is saved to disk immediately;
    - every successful AC judge call is saved immediately;
    - completed runs are skipped on resume;
    - if generation is already saved but evaluation was interrupted, generation is NOT repeated;
    - if some AC judge calls failed, only those failed/missing ACs are retried;
    - invalid JSON is regenerated immediately (up to 2 automatic retries) and is never scored as 0%.
    """
    checkpoint_path = _bulk_checkpoint_path(userstories, repetitions)
    checkpoint = _load_bulk_checkpoint(checkpoint_path)
    if checkpoint is None:
        checkpoint = _new_bulk_checkpoint(userstories, repetitions)
        _save_bulk_checkpoint(checkpoint_path, checkpoint)

    rows: List[Dict[str, Any]] = []
    runs_store: Dict[str, Any] = {}
    total_runs = len(userstories) * repetitions * 2
    done = 0
    api_generation_calls_this_resume = 0

    progress = st.progress(0)
    status = st.empty()

    variants = [
        ("without_ui_context", False),
        ("with_ui_context", True),
    ]

    for rep in range(1, repetitions + 1):
        for item in userstories:
            for variant_name, use_ui in variants:
                run_key = f"{item['id']}|{variant_name}|rep{rep}"
                run_state = checkpoint.setdefault("runs", {}).setdefault(run_key, {
                    "item": item,
                    "variant": variant_name,
                    "rep": rep,
                    "use_ui_context": use_ui,
                    "generation_complete": False,
                    "complete": False,
                    "cases": [],
                    "open_q": [],
                    "ac_judge": {"details": {}},
                })

                # Keep metadata current without throwing away saved work.
                run_state["item"] = item
                run_state["variant"] = variant_name
                run_state["rep"] = rep
                run_state["use_ui_context"] = use_ui
                run_state.setdefault("ac_judge", {}).setdefault("details", {})

                done += 1
                progress.progress(done / total_runs)

                # Repair checkpoints created by older versions that accidentally treated invalid JSON
                # as a real 0% result. Such a run is a technical generation failure, not a quality score.
                cached_failure = _generation_failure_reason(
                    run_state.get("cases", []) or [],
                    run_state.get("open_q", []) or [],
                )
                if cached_failure:
                    run_state["generation_complete"] = False
                    run_state["complete"] = False
                    run_state["cases"] = []
                    run_state["evaluation"] = None
                    run_state["row"] = None
                    # Any judge decisions from the invalid/empty generation belong to the bad output
                    # and must not be reused after regeneration.
                    run_state["ac_judge"] = {"details": {}}
                    run_state["last_error"] = (
                        f"{cached_failure} Previous 0% result invalidated; this run will be regenerated on resume."
                    )
                    _save_bulk_checkpoint(checkpoint_path, checkpoint)

                if run_state.get("complete") and run_state.get("row") and run_state.get("evaluation"):
                    # Reuse the already-paid generation, but recompute all metrics from
                    # the saved test cases. Local metrics (Role, Target Node, Navigation)
                    # cost nothing. AC judge calls are reused when they were already made
                    # with AC_JUDGE_VERSION; older judge results are re-judged without
                    # regenerating the test cases.
                    saved_cases = run_state.get("cases", []) or []
                    saved_open_q = run_state.get("open_q", []) or []
                    status.write(
                        f"Resume {done}/{total_runs}: {item['id']} — {variant_name} — repetition {rep}/{repetitions} — reusing saved generation; refreshing metrics"
                    )

                    refreshed_evaluation = evaluate_all(
                        us_id_value=item["id"],
                        story=item["story"],
                        ac_blob=item["ac_blob"],
                        cases=saved_cases,
                        use_ui_context=use_ui,
                        bulk_checkpoint_state=checkpoint,
                        bulk_checkpoint_path=checkpoint_path,
                        bulk_run_key=run_key,
                    )

                    ac_pct = _metric_or_none(refreshed_evaluation, "ac", "overall_pct")
                    role_pct = _metric_or_none(refreshed_evaluation, "role", "overall_pct")
                    target_pct = _metric_or_none(refreshed_evaluation, "target_node", "coverage_pct")
                    nav_pct = _metric_or_none(refreshed_evaluation, "navigation_path", "correctness_pct")
                    ac_incomplete = ac_pct is None
                    error_text = ""
                    if ac_incomplete:
                        error_text = (
                            "AC Coverage judge incomplete. Saved successful strict-judge calls will be reused; "
                            "resume to retry only failed/missing AC judge calls."
                        )

                    refreshed_row = dict(run_state.get("row") or {})
                    refreshed_row.update({
                        "repetition": rep,
                        "us_id": item["id"],
                        "title": item.get("title", ""),
                        "variant": variant_name,
                        "use_ui_context": use_ui,
                        "acceptance_criteria_count": item.get("acceptance_criteria_count"),
                        "testcase_count": len(saved_cases),
                        "ac_coverage_pct": ac_pct,
                        "role_coverage_pct": role_pct,
                        "target_node_coverage_pct": target_pct,
                        "navigation_path_correctness_pct": nav_pct,
                        "navigation_correctness_pct": nav_pct,
                        "overall_score_pct": _overall_score(ac_pct, role_pct, target_pct, nav_pct),
                        "open_questions_count": len(saved_open_q),
                        "error": error_text,
                    })

                    run_state["evaluation"] = refreshed_evaluation
                    run_state["row"] = refreshed_row
                    run_state["complete"] = not ac_incomplete
                    run_state["last_error"] = error_text
                    _save_bulk_checkpoint(checkpoint_path, checkpoint)

                    rows.append(refreshed_row)
                    runs_store[run_key] = {
                        "item": item,
                        "variant": variant_name,
                        "rep": rep,
                        "cases": saved_cases,
                        "open_q": saved_open_q,
                        "evaluation": refreshed_evaluation,
                    }
                    continue

                status.write(
                    f"Bulk run {done}/{total_runs}: {item['id']} — {variant_name} — repetition {rep}/{repetitions}"
                )

                try:
                    # Generation is the expensive part that must never be repeated after it succeeded.
                    if run_state.get("generation_complete"):
                        cases = run_state.get("cases", []) or []
                        open_q = run_state.get("open_q", []) or []
                        status.write(
                            f"Bulk run {done}/{total_runs}: {item['id']} — {variant_name} — using saved generation; continuing evaluation"
                        )
                    else:
                        # Invalid JSON is a technical generation failure, not a test-quality result.
                        # Retry it immediately so the bulk run can continue without waiting for a manual resume.
                        # The cap prevents an endless loop / uncontrolled API costs if the model repeatedly
                        # returns malformed output. Local JSON repair in _json_from_text() is attempted first.
                        max_invalid_json_retries = 2  # 1 initial call + up to 2 automatic re-generations
                        generation_attempt = 0

                        while True:
                            generation_attempt += 1
                            cases, open_q = generate_cases(
                                story=item["story"],
                                ac_blob=item["ac_blob"],
                                use_ui_context=use_ui,
                            )
                            api_generation_calls_this_resume += 1

                            generation_failure = _generation_failure_reason(cases, open_q)
                            invalid_json = generation_failure == "Model response was not valid JSON."

                            if invalid_json and generation_attempt <= max_invalid_json_retries:
                                run_state["generation_complete"] = False
                                run_state["complete"] = False
                                run_state["cases"] = []
                                run_state["open_q"] = open_q
                                run_state["evaluation"] = None
                                run_state["row"] = None
                                run_state["ac_judge"] = {"details": {}}
                                run_state["last_error"] = (
                                    f"Invalid JSON on generation attempt {generation_attempt}; "
                                    f"automatically regenerating ({generation_attempt}/{max_invalid_json_retries} retries used)."
                                )
                                _save_bulk_checkpoint(checkpoint_path, checkpoint)
                                status.write(
                                    f"Bulk run {done}/{total_runs}: {item['id']} — {variant_name} — "
                                    f"invalid JSON on attempt {generation_attempt}; regenerating automatically..."
                                )
                                continue

                            break

                        if generation_failure:
                            run_state["generation_complete"] = False
                            run_state["complete"] = False
                            run_state["cases"] = []
                            run_state["open_q"] = open_q
                            run_state["evaluation"] = None
                            run_state["row"] = None
                            run_state["ac_judge"] = {"details": {}}
                            if generation_failure == "Model response was not valid JSON.":
                                failure_suffix = (
                                    f" Automatic regeneration also failed after {generation_attempt} total attempts; "
                                    "excluded from all metric averages and left unfinished for a later resume."
                                )
                            else:
                                failure_suffix = (
                                    " Technical generation failure; excluded from all metric averages and retried on resume."
                                )
                            run_state["last_error"] = f"{generation_failure}{failure_suffix}"
                            _save_bulk_checkpoint(checkpoint_path, checkpoint)
                            rows.append({
                                "repetition": rep,
                                "us_id": item.get("id", ""),
                                "title": item.get("title", ""),
                                "variant": variant_name,
                                "use_ui_context": use_ui,
                                "acceptance_criteria_count": item.get("acceptance_criteria_count"),
                                "testcase_count": 0,
                                "ac_coverage_pct": None,
                                "role_coverage_pct": None,
                                "target_node_coverage_pct": None,
                                "navigation_path_correctness_pct": None,
                                "navigation_correctness_pct": None,
                                "overall_score_pct": None,
                                "open_questions_count": len(open_q or []),
                                "error": run_state["last_error"],
                            })
                            continue

                        # Save immediately after the first valid generation response returns, before any judge calls.
                        # Judge decisions are tied to this exact generated output, so a fresh generation
                        # starts with an empty judge cache.
                        run_state["generation_complete"] = True
                        run_state["cases"] = cases
                        run_state["open_q"] = open_q
                        run_state["ac_judge"] = {"details": {}}
                        run_state["last_error"] = ""
                        _save_bulk_checkpoint(checkpoint_path, checkpoint)

                    evaluation = evaluate_all(
                        us_id_value=item["id"],
                        story=item["story"],
                        ac_blob=item["ac_blob"],
                        cases=cases,
                        use_ui_context=use_ui,
                        bulk_checkpoint_state=checkpoint,
                        bulk_checkpoint_path=checkpoint_path,
                        bulk_run_key=run_key,
                    )

                    ac_pct = _metric_or_none(evaluation, "ac", "overall_pct")
                    role_pct = _metric_or_none(evaluation, "role", "overall_pct")
                    target_pct = _metric_or_none(evaluation, "target_node", "coverage_pct")
                    nav_pct = _metric_or_none(evaluation, "navigation_path", "correctness_pct")

                    ac_incomplete = ac_pct is None
                    error_text = ""
                    if ac_incomplete:
                        error_text = (
                            "AC Coverage judge incomplete. Saved successful judge calls will be reused; "
                            "resume to retry only failed/missing AC judge calls."
                        )

                    row = {
                        "repetition": rep,
                        "us_id": item["id"],
                        "title": item.get("title", ""),
                        "variant": variant_name,
                        "use_ui_context": use_ui,
                        "acceptance_criteria_count": item.get("acceptance_criteria_count"),
                        "testcase_count": len(cases),
                        "ac_coverage_pct": ac_pct,
                        "role_coverage_pct": role_pct,
                        "target_node_coverage_pct": target_pct,
                        "navigation_path_correctness_pct": nav_pct,
                        "navigation_correctness_pct": nav_pct,
                        "overall_score_pct": _overall_score(ac_pct, role_pct, target_pct, nav_pct),
                        "open_questions_count": len(open_q or []),
                        "error": error_text,
                    }

                    run_state["evaluation"] = evaluation
                    run_state["row"] = row
                    run_state["complete"] = not ac_incomplete
                    run_state["last_error"] = error_text
                    _save_bulk_checkpoint(checkpoint_path, checkpoint)

                    rows.append(row)
                    runs_store[run_key] = {
                        "item": item,
                        "variant": variant_name,
                        "rep": rep,
                        "cases": cases,
                        "open_q": open_q,
                        "evaluation": evaluation,
                    }

                except Exception as e:
                    # Save the current state before moving on. A resume will reuse any generation
                    # and AC judge calls that already completed successfully.
                    run_state["complete"] = False
                    run_state["last_error"] = str(e)
                    _save_bulk_checkpoint(checkpoint_path, checkpoint)
                    rows.append({
                        "repetition": rep,
                        "us_id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "variant": variant_name,
                        "use_ui_context": use_ui,
                        "acceptance_criteria_count": item.get("acceptance_criteria_count"),
                        "testcase_count": len(run_state.get("cases", []) or []),
                        "ac_coverage_pct": None,
                        "role_coverage_pct": None,
                        "target_node_coverage_pct": None,
                        "navigation_path_correctness_pct": None,
                        "navigation_correctness_pct": None,
                        "overall_score_pct": None,
                        "open_questions_count": len(run_state.get("open_q", []) or []),
                        "error": str(e),
                    })

    progress.progress(1.0)
    stats = _bulk_checkpoint_stats(checkpoint)
    if stats["completed"] == total_runs:
        status.write("Bulk evaluation finished. All runs are checkpointed on disk.")
    else:
        status.write(
            f"Bulk pass finished with {stats['completed']}/{total_runs} complete runs. "
            "Run / resume again to retry only unfinished work."
        )

    st.session_state.bulk_runs_store = runs_store
    st.session_state.bulk_checkpoint_path = checkpoint_path
    st.session_state.bulk_checkpoint_stats = stats
    st.session_state.bulk_generation_calls_this_resume = api_generation_calls_this_resume
    return pd.DataFrame(rows)


def summarize_bulk_results(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return pd.DataFrame()

    agg_dict = dict(
        attempted_runs=("variant", "count"),
        valid_runs=("ac_coverage_pct", "count"),
        user_stories=("us_id", "nunique"),
        avg_testcase_count=("testcase_count", "mean"),
        avg_ac_coverage_pct=("ac_coverage_pct", "mean"),
        std_ac_coverage_pct=("ac_coverage_pct", "std"),
        avg_role_coverage_pct=("role_coverage_pct", "mean"),
        std_role_coverage_pct=("role_coverage_pct", "std"),
        avg_target_node_coverage_pct=("target_node_coverage_pct", "mean"),
        std_target_node_coverage_pct=("target_node_coverage_pct", "std"),
        avg_navigation_path_correctness_pct=("navigation_path_correctness_pct", "mean"),
        std_navigation_path_correctness_pct=("navigation_path_correctness_pct", "std"),
        avg_navigation_correctness_pct=("navigation_correctness_pct", "mean"),
        std_navigation_correctness_pct=("navigation_correctness_pct", "std"),
        avg_overall_score_pct=("overall_score_pct", "mean"),
        std_overall_score_pct=("overall_score_pct", "std"),
        failed_runs=("error", lambda values: sum(bool(str(v).strip()) for v in values)),
    )

    summary = results_df.groupby("variant", dropna=False).agg(**agg_dict).reset_index()
    return summary.round(2)


def summarize_bulk_by_user_story(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return pd.DataFrame()

    agg_dict = dict(
        attempted_runs=("variant", "count"),
        valid_runs=("ac_coverage_pct", "count"),
        avg_testcase_count=("testcase_count", "mean"),
        avg_ac_coverage_pct=("ac_coverage_pct", "mean"),
        avg_role_coverage_pct=("role_coverage_pct", "mean"),
        avg_target_node_coverage_pct=("target_node_coverage_pct", "mean"),
        avg_navigation_path_correctness_pct=("navigation_path_correctness_pct", "mean"),
        avg_navigation_correctness_pct=("navigation_correctness_pct", "mean"),
        avg_overall_score_pct=("overall_score_pct", "mean"),
        failed_runs=("error", lambda values: sum(bool(str(v).strip()) for v in values)),
    )

    by_us = results_df.groupby(["us_id", "title", "variant"], dropna=False).agg(**agg_dict).reset_index()
    return by_us.round(2)

# ======================= PDF BUILDER =======================
def build_pdf(
    story_text: str,
    ac_blob: str,
    cases: list,
    open_questions: list,
    evaluation: Optional[Dict[str, Any]] = None,
    us_id_value: str = ""
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=22)
    head = ParagraphStyle("h", parent=styles["Heading2"], fontSize=14)
    body = ParagraphStyle("b", parent=styles["Normal"], fontSize=11, leading=14)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=10, leading=13, wordWrap="CJK")

    flow = []
    flow.append(Paragraph("User Story to Testcase Generator", title))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph("<b>User Story ID</b>", head))
    flow.append(Paragraph(us_id_value.strip() or "—", body))
    flow.append(Spacer(1, 8))

    flow.append(Paragraph("<b>User Story</b>", head))
    flow.append(Paragraph(story_text.strip() or "—", body))
    flow.append(Spacer(1, 8))

    flow.append(Paragraph("<b>Acceptance Criteria</b>", head))
    lines = [l.strip() for l in ac_blob.splitlines() if l.strip()]
    if lines:
        flow.append(
            ListFlowable(
                [ListItem(Paragraph(l, body), leftIndent=6) for l in lines],
                bulletType="bullet",
                leftPadding=12,
            )
        )
    else:
        flow.append(Paragraph("—", body))
    flow.append(Spacer(1, 12))

    if evaluation:
        flow.append(Paragraph("<b>Automated Evaluation</b>", head))
        ac_value = "N/A" if evaluation["ac"]["overall_pct"] is None else f"{evaluation['ac']['covered_count']}/{evaluation['ac']['total_count']} ({evaluation['ac']['overall_pct']}%)"
        target_value = "N/A" if evaluation.get("target_node", {}).get("coverage_pct") is None else f"{evaluation['target_node']['covered_count']}/{evaluation['target_node']['total_count']} ({evaluation['target_node']['coverage_pct']}%)"
        nav_corr_value = "N/A" if evaluation["navigation_path"]["correctness_pct"] is None else f"{evaluation['navigation_path']['correct_count']}/{evaluation['navigation_path']['evaluated_count']} ({evaluation['navigation_path']['correctness_pct']}%)"
        role_value = "N/A" if evaluation["role"]["overall_pct"] is None else f"{evaluation['role']['covered_count']}/{evaluation['role']['total_count']} ({evaluation['role']['overall_pct']}%)"

        rows = [
            ["Metric", "Value"],
            ["AC Coverage", ac_value],
            ["Target Node Coverage", target_value],
            ["Navigation Path Correctness", nav_corr_value],
            ["Role Coverage", role_value],
            ["Test Cases", str(len(cases))]
        ]

        t = Table(rows, colWidths=[180, 260])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        flow.append(t)
        flow.append(Spacer(1, 12))

    if open_questions:
        flow.append(Paragraph("<b>Open Questions</b>", head))
        cleaned_open_questions = _clean_open_questions(open_questions)
        flow.append(
            ListFlowable(
                [ListItem(Paragraph(q, body), leftIndent=6) for q in cleaned_open_questions],
                bulletType="bullet",
                leftPadding=12,
            )
        )
        flow.append(Spacer(1, 12))

    if cases:
        flow.append(Paragraph("<b>Generated Test Design</b>", head))
        flow.append(Spacer(1, 6))

        trows = [["ID", "Title", "Priority", "Type"]]
        for tc in cases:
            trows.append(
                [
                    Paragraph(tc.get("id", "") or "", cell),
                    Paragraph(tc.get("title", "") or "", cell),
                    Paragraph(tc.get("priority", "") or "", cell),
                    Paragraph(tc.get("type", "") or "", cell),
                ]
            )

        t = Table(trows, colWidths=[50, 300, 70, 70])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        flow.append(t)
        flow.append(Spacer(1, 12))

        for tc in cases:
            flow.append(Paragraph(f"<b>{tc.get('id','')}</b> — {tc.get('title','')}", styles["Heading3"]))
            steps = tc.get("steps", []) or []

            step_rows = [
                [
                    Paragraph("Step", styles["Heading5"]),
                    Paragraph("Action", styles["Heading5"]),
                    Paragraph("Expected Result", styles["Heading5"]),
                ]
            ]

            for i, s in enumerate(steps, start=1):
                step_rows.append(
                    [
                        Paragraph(str(i), cell),
                        Paragraph(s.get("step", "") or "—", cell),
                        Paragraph(s.get("expected", "") or "—", cell),
                    ]
                )

            st_table = Table(step_rows, colWidths=[35, 230, 255])
            st_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            flow.append(st_table)
            flow.append(Spacer(1, 10))
    else:
        flow.append(Paragraph("<b>No test cases were generated.</b>", styles["Normal"]))

    doc.build(flow)
    return buf.getvalue()

# ======================= EVALUATION DISPLAY HELPER =======================
def _render_evaluation_results(ev: Dict[str, Any], header: str = "Automated Evaluation"):
    """Render metric values and the evidence/reasoning behind every metric."""

    def _path_str(node_ids: List[str]) -> str:
        name_map = _node_name_map()
        names = [name_map.get(nid, nid) for nid in node_ids]
        return " → ".join(names) if names else "—"

    def _status(ok: bool) -> str:
        return "Covered" if ok else "Not covered"

    st.subheader(header)

    ac = ev.get("ac", {})
    target_node = ev.get("target_node", {})
    nav = ev.get("navigation_path", {})
    role = ev.get("role", {})

    ac_metric = "N/A" if ac.get("overall_pct") is None else f"{ac['overall_pct']}%"
    target_metric = "N/A" if target_node.get("coverage_pct") is None else f"{target_node['coverage_pct']}%"
    nav_metric = "N/A" if nav.get("correctness_pct") is None else f"{nav['correctness_pct']}%"
    role_metric = "N/A" if role.get("overall_pct") is None else f"{role['overall_pct']}%"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("AC Coverage", ac_metric)
    c2.metric("Role Coverage", role_metric)
    c3.metric("Target Node Coverage", target_metric)
    c4.metric("Navigation Path Correctness", nav_metric)

    # AC Coverage details and judge reasons.
    st.write("**AC Coverage**")
    if ac.get("note"):
        st.warning(ac["note"])
    else:
        st.write(f"{ac.get('covered_count', 0)}/{ac.get('total_count', 0)} acceptance criteria covered")
        with st.expander("AC Coverage details and reasons"):
            for d in ac.get("details", []):
                covered = bool(d.get("covered"))
                st.write(f"**{d.get('ac_id', '')} — {_status(covered)}**")
                st.write(d.get("ac_text", ""))
                st.caption(f"Reason: {d.get('reason') or 'No reason returned.'}")

    # Role Coverage details.
    st.write("**Role Coverage**")
    required_roles = role.get("required_roles", []) or []
    generated_roles = role.get("generated_roles", []) or []
    missing_roles = role.get("missing_roles", []) or []
    if role.get("overall_pct") is None and not required_roles:
        st.caption("No required user roles were found in this user story or its acceptance criteria.")
    else:
        st.write(f"{role.get('covered_count', 0)}/{role.get('total_count', 0)} required roles covered")
        with st.expander("Role Coverage details and reasons"):
            for role_name in required_roles:
                covered = role_name in generated_roles
                if covered:
                    reason = f"An explicit role/login reference for '{role_name}' was found in the generated test cases."
                else:
                    reason = f"No explicit role/login reference for '{role_name}' was found in the generated test cases."
                st.write(f"**{role_name.title()} — {_status(covered)}**")
                st.caption(f"Reason: {reason}")
            if missing_roles:
                st.caption(f"Missing roles: {', '.join(missing_roles)}")

    # Target Node Coverage details.
    st.write("**Target Node Coverage**")
    if target_node.get("note"):
        st.info(target_node["note"])
    else:
        st.write(
            f"{target_node.get('covered_count', 0)}/{target_node.get('total_count', 0)} "
            "required_across_story target nodes reached"
        )
        with st.expander("Target Node Coverage details and reasons"):
            for d in target_node.get("details", []):
                covered = bool(d.get("covered"))
                node_id = d.get("node_id", "")
                node_name = d.get("node_name", node_id)
                if covered:
                    reason = (
                        "The expected target node is reached by an explicit ui_node_id or by the immediate "
                        "target of an explicitly activated relationship in ui_context.json."
                    )
                else:
                    reason = (
                        "The expected target node is neither emitted as a ui_node_id nor reached as the immediate "
                        "target of an explicitly activated relationship in ui_context.json."
                    )
                st.write(f"**{node_id} — {node_name} — {_status(covered)}**")
                st.caption(f"Reason: {reason}")

    # Navigation Path Correctness details.
    st.write("**Navigation Path Correctness**")
    if nav.get("note"):
        st.info(nav["note"])
    else:
        skipped = nav.get("skipped_count") or 0
        skip_note = f"; {skipped} skipped" if skipped else ""
        st.write(
            f"{nav.get('correct_count', 0)}/{nav.get('evaluated_count', 0)} "
            f"evaluable test-case paths correct{skip_note}"
        )
        st.caption(
            "Each test case must contain all required_per_testcase nodes in the correct order. "
            "Additional or repeated known UI nodes are allowed and are not evaluated as direct transitions. "
            "required_across_story is scored separately under Target Node Coverage."
        )
        with st.expander("Navigation Path Correctness details and reasons"):
            for d in nav.get("details", []):
                tc_id = d.get("tc_id", "")
                target = d.get("selected_target", "")
                can_evaluate = bool(d.get("can_evaluate"))

                if not can_evaluate:
                    st.write(f"**{tc_id or 'Test case'} — Skipped**")
                    st.caption(f"Reason: {d.get('skip_reason') or 'No evaluable navigation path.'}")
                    continue

                is_correct = bool(d.get("is_correct"))
                expected = d.get("expected", []) or []
                actual = d.get("actual", []) or []
                missing = d.get("missing_nodes", []) or []

                invalid_ui_node_ids = d.get("invalid_ui_node_ids", []) or []
                invalid_transitions = d.get("invalid_transitions", []) or []
                if is_correct:
                    reason = (
                        "All required_per_testcase nodes occur in the required order. Additional or repeated known UI nodes are allowed."
                    )
                elif missing:
                    reason = f"Required per-testcase nodes are missing: {_path_str(missing)}."
                elif invalid_ui_node_ids:
                    reason = f"Unknown ui_node_id value(s) not found in ui_context.json: {', '.join(invalid_ui_node_ids)}."
                else:
                    reason = "The required per-testcase nodes are present but do not occur in the required order."

                st.write(
                    f"**{tc_id or 'Test case'} — {target or 'navigation path'} — "
                    f"{'Correct' if is_correct else 'Incorrect'}**"
                )
                st.caption(f"Expected: {_path_str(expected)}")
                st.caption(f"Actual: {_path_str(actual)}")
                st.caption(f"Reason: {reason}")


# ======================= SESSION STATE =======================
if "last_pdf" not in st.session_state:
    st.session_state.last_pdf = None
if "last_open_questions" not in st.session_state:
    st.session_state.last_open_questions = []
if "last_cases_count" not in st.session_state:
    st.session_state.last_cases_count = 0
if "last_variant" not in st.session_state:
    st.session_state.last_variant = None
if "last_cases" not in st.session_state:
    st.session_state.last_cases = []
if "last_evaluation" not in st.session_state:
    st.session_state.last_evaluation = None

if "single_export_pdf" not in st.session_state:
    st.session_state.single_export_pdf = None
if "single_export_filename" not in st.session_state:
    st.session_state.single_export_filename = "single_test_design.pdf"
if "single_export_info" not in st.session_state:
    st.session_state.single_export_info = ""
if "single_cases" not in st.session_state:
    st.session_state.single_cases = []
if "single_open_questions" not in st.session_state:
    st.session_state.single_open_questions = []
if "single_evaluation" not in st.session_state:
    st.session_state.single_evaluation = None
if "single_selected_item" not in st.session_state:
    st.session_state.single_selected_item = None
if "single_variant_slug" not in st.session_state:
    st.session_state.single_variant_slug = None

# ======================= BUTTONS =======================
st.markdown('<div class="export-wrap">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    clicked_without = st.button(
        "Export without UI context",
        disabled=not (user_story.strip() and ac_text.strip())
    )

with col2:
    clicked_with = st.button(
        "Export with UI context",
        disabled=not (user_story.strip() and ac_text.strip())
    )

with col3:
    clicked_eval = st.button(
        "Evaluate current output",
        disabled=not (bool(st.session_state.last_cases) and us_id.strip())
    )


st.markdown('</div>', unsafe_allow_html=True)

if clicked_without or clicked_with:
    use_ui = clicked_with

    with st.spinner("Generating test cases and building PDF..."):
        cases, open_q = generate_cases(user_story, ac_text, use_ui_context=use_ui)
        pdf_bytes = build_pdf(user_story, ac_text, cases, open_q, evaluation=None, us_id_value=us_id.strip())

        st.session_state.last_pdf = pdf_bytes
        st.session_state.last_open_questions = open_q
        st.session_state.last_cases_count = len(cases)
        st.session_state.last_variant = "with_json" if use_ui else "without_json"
        st.session_state.last_cases = cases
        st.session_state.last_evaluation = None

if clicked_eval and st.session_state.last_cases:
    if not us_id.strip():
        st.warning("Please enter a User Story ID before running the evaluation. The ID is only required for evaluation, not for PDF generation.")
        st.stop()

    evaluation = evaluate_all(
        us_id.strip(),
        user_story,
        ac_text,
        st.session_state.last_cases,
        use_ui_context=(st.session_state.last_variant == "with_json"),
    )
    st.session_state.last_evaluation = evaluation
    st.session_state.last_pdf = build_pdf(
        user_story,
        ac_text,
        st.session_state.last_cases,
        st.session_state.last_open_questions,
        evaluation=evaluation,
        us_id_value=us_id.strip()
    )

# ======================= OUTPUT =======================
if st.session_state.last_variant:
    st.info(f"Generated with: {st.session_state.last_variant}")

if st.session_state.last_open_questions:
    cleaned_open_questions = _clean_open_questions(st.session_state.last_open_questions)
    st.warning("Notes / Open Questions:\n- " + "\n- ".join(cleaned_open_questions))

if st.session_state.last_evaluation:
    _render_evaluation_results(st.session_state.last_evaluation, "Automated Evaluation")

if st.session_state.last_pdf:
    st.success(f"PDF ready (test cases: {st.session_state.last_cases_count})")
    st.download_button(
        "Download PDF",
        data=st.session_state.last_pdf,
        file_name=f"test_design_{us_id}_{st.session_state.last_variant or 'result'}.pdf",
        mime="application/pdf",
    )




# ======================= SINGLE EXPORT FROM BULK USER STORIES =======================
st.markdown("---")
st.subheader("Single User Story Export")
st.write(
    "Enter a user story number, for example `1` or `US-1`. The app loads the matching entry "
    "from `bulk_userstories.json`. First generate the test cases/PDF, then run the single evaluation "
    "with the separate evaluation button if needed."
)

single_col1, single_col2 = st.columns([1, 1])
with single_col1:
    single_us_lookup = st.text_input(
        "User Story number",
        key="single_us_lookup",
        placeholder="e.g. 1 or US-1"
    )
with single_col2:
    single_variant_choice = st.radio(
        "Variant",
        ["with UI context", "without UI context"],
        horizontal=False,
        key="single_variant_choice"
    )

single_btn_col1, single_btn_col2 = st.columns([1, 1])
with single_btn_col1:
    single_export_clicked = st.button(
        "Generate single export",
        disabled=not single_us_lookup.strip(),
        key="single_export_button"
    )
with single_btn_col2:
    single_eval_clicked = st.button(
        "Evaluate single export",
        disabled=not bool(st.session_state.single_cases),
        key="single_eval_button"
    )


if single_export_clicked:
    try:
        bulk_items_for_single = load_bulk_userstories(BULK_USERSTORIES_PATH)
        selected_item = find_userstory_by_id(bulk_items_for_single, single_us_lookup)

        if selected_item is None:
            available_ids = ", ".join(item["id"] for item in bulk_items_for_single[:10])
            st.error(
                f"No matching user story found for '{single_us_lookup}'. "
                f"Example available IDs: {available_ids}"
            )
        else:
            use_ui_single = single_variant_choice == "with UI context"
            variant_slug = "with_json" if use_ui_single else "without_json"

            with st.spinner(f"Generating single export for {selected_item['id']}..."):
                single_cases, single_open_q = generate_cases(
                    selected_item["story"],
                    selected_item["ac_blob"],
                    use_ui_context=use_ui_single,
                )

                single_pdf = build_pdf(
                    selected_item["story"],
                    selected_item["ac_blob"],
                    single_cases,
                    single_open_q,
                    evaluation=None,
                    us_id_value=selected_item["id"],
                )

            st.session_state.single_selected_item = selected_item
            st.session_state.single_variant_slug = variant_slug
            st.session_state.single_cases = single_cases
            st.session_state.single_open_questions = single_open_q
            st.session_state.single_evaluation = None
            st.session_state.single_export_pdf = single_pdf
            st.session_state.single_export_filename = f"test_design_{selected_item['id']}_{variant_slug}.pdf"
            st.session_state.single_export_info = (
                f"Single export ready for {selected_item['id']} — {variant_slug} "
                f"(test cases: {len(single_cases)}). Evaluation not run yet."
            )
            st.success(st.session_state.single_export_info)

    except Exception as e:
        st.session_state.single_export_pdf = None
        st.session_state.single_cases = []
        st.session_state.single_open_questions = []
        st.session_state.single_evaluation = None
        st.session_state.single_selected_item = None
        st.session_state.single_variant_slug = None
        st.error(f"Single export failed: {e}")

if single_eval_clicked:
    try:
        selected_item = st.session_state.single_selected_item
        if not selected_item:
            st.warning("Generate a single export first, then run the single evaluation.")
        else:
            use_ui_single = st.session_state.single_variant_slug == "with_json"
            with st.spinner(f"Evaluating single export for {selected_item['id']}..."):
                single_evaluation = evaluate_all(
                    selected_item["id"],
                    selected_item["story"],
                    selected_item["ac_blob"],
                    st.session_state.single_cases,
                    use_ui_context=use_ui_single,
                )
                single_pdf = build_pdf(
                    selected_item["story"],
                    selected_item["ac_blob"],
                    st.session_state.single_cases,
                    st.session_state.single_open_questions,
                    evaluation=single_evaluation,
                    us_id_value=selected_item["id"],
                )

            st.session_state.single_evaluation = single_evaluation
            st.session_state.single_export_pdf = single_pdf
            st.session_state.single_export_info = (
                f"Single evaluation ready for {selected_item['id']} — {st.session_state.single_variant_slug} "
                f"(test cases: {len(st.session_state.single_cases)})"
            )
            st.success(st.session_state.single_export_info)
    except Exception as e:
        st.error(f"Single evaluation failed: {e}")

if st.session_state.single_selected_item:
    st.info(
        f"Current single export: {st.session_state.single_selected_item['id']} — "
        f"{st.session_state.single_variant_slug or 'not generated'}"
    )

if st.session_state.single_open_questions:
    cleaned_single_open_questions = _clean_open_questions(st.session_state.single_open_questions)
    st.warning("Single export notes / Open Questions:\n- " + "\n- ".join(cleaned_single_open_questions))

if st.session_state.single_evaluation:
    _render_evaluation_results(st.session_state.single_evaluation, "Single Export Evaluation")

if st.session_state.single_export_pdf:
    if st.session_state.single_export_info:
        st.info(st.session_state.single_export_info)
    st.download_button(
        "Download single export PDF",
        data=st.session_state.single_export_pdf,
        file_name=st.session_state.single_export_filename,
        mime="application/pdf",
        key="single_export_download",
    )


# ======================= BULK EVALUATION UI =======================
st.markdown("---")
st.subheader("Bulk Evaluation")
st.write(
    "This runs all user stories in a bulk JSON file. For every user story, the tool generates "
    "test cases once without UI context and once with UI context. You can repeat the whole run "
    "multiple times to get more stable average scores."
)

bulk_repetitions = st.number_input(
    "How many repetitions per variant?",
    min_value=1,
    max_value=20,
    value=3,
    step=1,
    help="Example: 3 repetitions with 24 user stories means 24 × 2 variants × 3 = 144 LLM calls."
)


bulk_uploaded_file = st.file_uploader(
    "Optional: upload bulk_userstories.json. If nothing is uploaded, the app tries to use the local bulk_userstories.json file.",
    type=["json"],
    key="bulk_userstories_upload",
)

try:
    if bulk_uploaded_file is not None:
        preview_userstories = load_bulk_userstories(bulk_uploaded_file)
        bulk_uploaded_file.seek(0)
        st.info(f"Uploaded bulk file contains {len(preview_userstories)} user stories.")
    elif os.path.exists(BULK_USERSTORIES_PATH):
        preview_userstories = load_bulk_userstories(BULK_USERSTORIES_PATH)
        st.info(f"Local {BULK_USERSTORIES_PATH} contains {len(preview_userstories)} user stories.")
    else:
        preview_userstories = []
        st.warning(f"No uploaded file and no local {BULK_USERSTORIES_PATH} found.")
except Exception as e:
    preview_userstories = []
    st.error(f"Could not preview bulk user stories: {e}")

generation_calls = len(preview_userstories) * int(bulk_repetitions) * 2
judge_calls = sum(item.get("acceptance_criteria_count", 0) for item in preview_userstories) * int(bulk_repetitions) * 2
estimated_calls = generation_calls + judge_calls
st.caption(
    f"Maximum calls for a completely new run: {estimated_calls} "
    f"({generation_calls} generation + {judge_calls} AC Coverage judge calls). "
    "Resume mode does not repeat already checkpointed work."
)

current_checkpoint_path = (
    _bulk_checkpoint_path(preview_userstories, int(bulk_repetitions))
    if preview_userstories else None
)
current_checkpoint = _load_bulk_checkpoint(current_checkpoint_path) if current_checkpoint_path else None
checkpoint_stats = _bulk_checkpoint_stats(current_checkpoint)
total_expected_runs = len(preview_userstories) * int(bulk_repetitions) * 2

if current_checkpoint:
    st.success(
        f"Saved checkpoint found: {checkpoint_stats['completed']}/{total_expected_runs} runs complete; "
        f"{checkpoint_stats['generated']} generations already saved; "
        f"{checkpoint_stats['judge_done']} AC judge decisions already saved. "
        "Starting again will resume from this checkpoint instead of paying for those calls again."
    )
    if checkpoint_stats["judge_failed"]:
        st.warning(
            f"{checkpoint_stats['judge_failed']} AC judge call(s) previously failed. "
            "Only those failed/missing judge calls will be retried."
        )

bulk_btn_col1, bulk_btn_col2 = st.columns([2, 1])
with bulk_btn_col1:
    run_bulk_button = st.button(
        "Run / resume bulk evaluation",
        disabled=not (client and preview_userstories),
        type="primary",
    )
with bulk_btn_col2:
    clear_checkpoint_button = st.button(
        "Clear saved checkpoint",
        disabled=not bool(current_checkpoint),
        help="Deletes saved bulk progress for the currently selected dataset and repetition count. Use only when you intentionally want to start from scratch.",
    )

if clear_checkpoint_button and current_checkpoint_path:
    _delete_bulk_checkpoint(current_checkpoint_path)
    for key in [
        "bulk_results_df",
        "bulk_summary_df",
        "bulk_by_us_df",
        "bulk_runs_store",
        "bulk_checkpoint_path",
        "bulk_checkpoint_stats",
    ]:
        st.session_state.pop(key, None)
    st.success("Saved checkpoint cleared. The next run will start from scratch.")
    st.rerun()

if run_bulk_button:
    try:
        # Reload file so the stream position is correct.
        if bulk_uploaded_file is not None:
            bulk_uploaded_file.seek(0)
            bulk_userstories = load_bulk_userstories(bulk_uploaded_file)
        else:
            bulk_userstories = load_bulk_userstories(BULK_USERSTORIES_PATH)

        with st.spinner(
            "Running/resuming bulk evaluation. Completed generations and AC judge calls are reused from disk."
        ):
            results_df = run_bulk_evaluation(bulk_userstories, int(bulk_repetitions))
            summary_df = summarize_bulk_results(results_df)
            by_us_df = summarize_bulk_by_user_story(results_df)

        st.session_state.bulk_results_df = results_df
        st.session_state.bulk_summary_df = summary_df
        st.session_state.bulk_by_us_df = by_us_df

        stats = st.session_state.get("bulk_checkpoint_stats", {})
        if stats:
            st.success(
                f"Checkpoint saved: {stats.get('completed', 0)}/{len(bulk_userstories) * int(bulk_repetitions) * 2} runs complete. "
                "If the app stops, rerun with the same dataset and repetition count and press Run / resume."
            )

    except Exception as e:
        st.error(
            f"Bulk evaluation stopped: {e}. Progress already written to the checkpoint remains available. "
            "Press Run / resume bulk evaluation to continue without repeating completed work."
        )

if "bulk_summary_df" in st.session_state and not st.session_state.bulk_summary_df.empty:
    st.subheader("Bulk Summary")

    summary_for_metrics = st.session_state.bulk_summary_df.copy()
    with_ui_row = summary_for_metrics[summary_for_metrics["variant"] == "with_ui_context"]
    without_ui_row = summary_for_metrics[summary_for_metrics["variant"] == "without_ui_context"]

    def _fmt_pct(value):
        try:
            if pd.isna(value):
                return "N/A"
            return f"{float(value):.2f}%"
        except Exception:
            return "N/A"

    def _row_or_none(df):
        return None if df.empty else df.iloc[0]

    with_ui = _row_or_none(with_ui_row)
    without_ui = _row_or_none(without_ui_row)

    failed_total = 0
    if "failed_runs" in summary_for_metrics.columns:
        try:
            failed_total = int(summary_for_metrics["failed_runs"].fillna(0).sum())
        except Exception:
            failed_total = 0
    if failed_total:
        st.warning(
            f"{failed_total} technical/incomplete bulk run(s) are excluded from metric averages. "
            "Use Run / resume bulk evaluation to retry only those unfinished runs. Invalid JSON is never counted as 0% quality."
        )

    st.markdown("### Variant comparison")
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("#### With UI Context")
        if with_ui is not None:
            st.metric("AC Coverage", _fmt_pct(with_ui["avg_ac_coverage_pct"]))
            st.metric("Role Coverage", _fmt_pct(with_ui["avg_role_coverage_pct"]))
            st.metric("Target Node Coverage", _fmt_pct(with_ui["avg_target_node_coverage_pct"]))
            st.metric("Navigation Path Correctness", _fmt_pct(with_ui["avg_navigation_path_correctness_pct"]))
            st.metric("Overall Score", _fmt_pct(with_ui["avg_overall_score_pct"]))
        else:
            st.warning("No results for with_ui_context.")

    with right_col:
        st.markdown("#### Without UI Context")
        if without_ui is not None:
            st.metric("AC Coverage", _fmt_pct(without_ui["avg_ac_coverage_pct"]))
            st.metric("Role Coverage", _fmt_pct(without_ui["avg_role_coverage_pct"]))
            st.metric("Target Node Coverage", _fmt_pct(without_ui["avg_target_node_coverage_pct"]))
            st.metric("Navigation Path Correctness", _fmt_pct(without_ui["avg_navigation_path_correctness_pct"]))
            st.caption("Target Node Coverage and Navigation Path Correctness are N/A here: without UI context, no reliable explicit ui_node_id nodes/path are generated.")
            st.metric("Overall Score", _fmt_pct(without_ui["avg_overall_score_pct"]))
        else:
            st.warning("No results for without_ui_context.")

    st.info(
        "Overall Score is calculated as the average of the available metrics. "
        "Without UI context it includes AC Coverage and Role Coverage. "
        "With UI context it additionally includes Target Node Coverage and Navigation Path Correctness, because only that variant provides explicit ui_node_id nodes and paths."
    )

    st.markdown("### Summary table")
    st.dataframe(st.session_state.bulk_summary_df, use_container_width=True)

    summary_csv = st.session_state.bulk_summary_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "download bulk summary CSV",
        data=summary_csv,
        file_name="bulk_evaluation_summary.csv",
        mime="text/csv",
    )

if "bulk_by_us_df" in st.session_state and not st.session_state.bulk_by_us_df.empty:
    with st.expander("Bulk results by User Story"):
        st.dataframe(st.session_state.bulk_by_us_df, use_container_width=True)
        by_us_csv = st.session_state.bulk_by_us_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "download user-story summary CSV",
            data=by_us_csv,
            file_name="bulk_evaluation_by_user_story.csv",
            mime="text/csv",
        )

if st.session_state.get("bulk_checkpoint_path") and os.path.exists(st.session_state.bulk_checkpoint_path):
    try:
        with open(st.session_state.bulk_checkpoint_path, "rb") as checkpoint_file:
            checkpoint_bytes = checkpoint_file.read()
        st.download_button(
            "Download bulk checkpoint backup",
            data=checkpoint_bytes,
            file_name=os.path.basename(st.session_state.bulk_checkpoint_path),
            mime="application/json",
            help="Optional backup of all saved generations and AC judge decisions from the current bulk run.",
        )
    except Exception as e:
        st.warning(f"Could not prepare checkpoint download: {e}")

if "bulk_results_df" in st.session_state and not st.session_state.bulk_results_df.empty:
    with st.expander("Raw bulk result rows"):
        st.dataframe(st.session_state.bulk_results_df, use_container_width=True)
        raw_csv = st.session_state.bulk_results_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "download raw bulk results CSV",
            data=raw_csv,
            file_name="bulk_evaluation_raw_results.csv",
            mime="text/csv",
        )

# ======================= BULK RUN DETAILS + PDF EXPORT =======================
if "bulk_runs_store" in st.session_state and st.session_state.bulk_runs_store:
    st.markdown("---")
    st.subheader("Bulk Run Details")
    st.write("Select a User Story, variant and repetition to inspect every metric and its reasons, or export the corresponding PDF.")

    store = st.session_state.bulk_runs_store
    valid_keys = [k for k, v in store.items() if "cases" in v]

    if not valid_keys:
        st.warning("No successful runs available for PDF export.")
    else:
        # Parse keys into selectable options
        # key format: "US-1|with_ui_context|rep1"
        df_runs = st.session_state.bulk_results_df
        us_ids   = sorted(df_runs["us_id"].unique().tolist())
        variants = ["with_ui_context", "without_ui_context"]
        reps     = sorted(df_runs["repetition"].unique().tolist())

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            sel_us  = st.selectbox("User Story", us_ids, key="bulk_pdf_us")
        with pc2:
            sel_var = st.selectbox("Variant", variants, key="bulk_pdf_var")
        with pc3:
            sel_rep = st.selectbox("Repetition", reps, key="bulk_pdf_rep")

        run_key = f"{sel_us}|{sel_var}|rep{sel_rep}"
        run_data = store.get(run_key)

        if run_data and "cases" in run_data:
            item       = run_data["item"]
            cases      = run_data["cases"]
            open_q     = run_data["open_q"]
            evaluation = run_data["evaluation"]

            st.caption(f"Generated test cases: {len(cases)}")
            _render_evaluation_results(
                evaluation,
                f"Evaluation details — {sel_us} / {sel_var} / repetition {sel_rep}",
            )

            pdf_bytes = build_pdf(
                story_text=item["story"],
                ac_blob=item["ac_blob"],
                cases=cases,
                open_questions=open_q,
                evaluation=evaluation,
                us_id_value=item["id"],
            )
            st.download_button(
                f"Download PDF — {sel_us} / {sel_var} / rep {sel_rep}",
                data=pdf_bytes,
                file_name=f"test_design_{sel_us}_{sel_var}_rep{sel_rep}.pdf",
                mime="application/pdf",
                key="bulk_pdf_download",
            )
        else:
            st.warning(f"No data available for {run_key}. This run may have failed.")
