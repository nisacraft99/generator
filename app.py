# app.py
# Run:
#   pip install streamlit python-dotenv reportlab openai
#   streamlit run app.py

import os
import io
import json
import re
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
    page_title="💖 User Story → Testcase Generator",
    page_icon="✨",
    layout="wide"
)

# ======================= GLOBAL FONT =======================
st.markdown("""
<style>
:root { --comic: "Comic Sans MS","Comic Sans",cursive; }

html, body, .stApp, .stAppViewContainer, .main, .block-container,
.stMarkdown, .stAlert, .stDataFrame, .stForm,
.stTextInput, .stTextArea, .stSelectbox, .stMultiSelect, .stNumberInput,
.stButton > button, .stDownloadButton > button,
label, p {
  font-family: var(--comic) !important;
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
        st.session_state.pw_error = "Wrong password 🫠"

if not st.session_state.auth_ok:
    st.markdown("""
    <style>
      .stApp { background:#dff7f7; }

      .login-card{
        max-width: 640px; margin: 10vh auto; padding: 28px 30px;
        border-radius: 22px; border: 2px solid #a3d9ff;
        background:#ffffffcc; backdrop-filter: blur(6px);
        box-shadow: 0 12px 28px rgba(91,153,255,.25);
        text-align:center;
      }

      .login-title{
        display:block;
        margin: 0 auto 18px auto;
        padding: 12px 24px;
        border-radius:18px; border:2px solid #b98db0;
        background:#f8c9ea; color:#333;
        font-size: 42px; font-weight: 800;
      }

      .login-note{ color:#355c7d; font-size:16px; margin:6px 0 20px; }

      .login-card .stTextInput > div > div > input{
        border-radius: 16px; border:2px solid #bfe1ff;
        background:#f9ffff;
        font-size: 28px;
        height: 70px;
        width: 100% !important;
        padding: 10px 20px;
      }

      .login-card .stButton { text-align:center; margin-top:16px; }
      .login-card .stButton>button{
        border:none; border-radius:999px; padding:1rem 2rem; font-weight:700;
        font-size: 24px;
        background: linear-gradient(135deg,#bfe1ff,#9fd2ff);
        box-shadow:0 8px 18px rgba(159,210,255,.45); color:#123;
        min-width: 200px;
      }
      .login-card .stButton>button:hover{ filter:brightness(1.05); }
    </style>

    <div class="login-card">
      <div class="login-title">User Story to Testcase Generator</div>
      <p class="login-note">🔒 private app! please enter the password to continue.</p>
    """, unsafe_allow_html=True)

    st.text_input("Password", type="password", key="pw_input", label_visibility="collapsed")
    st.button("let me in! ✨", on_click=try_login)

    if st.session_state.get("pw_error"):
        st.error(st.session_state["pw_error"])

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ======================= MAIN UI =======================
st.markdown("""
<style>
.stApp { background: #ccf4f4 !important; }

.mock-title {
  margin: 25px auto 30px auto; width: 800px;
  background: #f7d8ef; border: 3px solid #000; border-radius: 14px;
  text-align: center; font-weight: 800; font-size: 40px; padding: 10px 16px;
}

.mock-label { font-weight: 500; font-size: 25px; color: #000; margin: 12px 0 6px 40px; }
.field-single, .field-multi { width: 900px; margin-left: 40px; }

.stTextArea textarea,
.stTextInput input {
  background: #fff4c7 !important;
  border: 3px solid #000 !important;
  border-radius: 16px !important;
  color: #000 !important;
  font-size: 18px !important;
  padding: 12px 16px !important;
  box-shadow: none !important;
  line-height: 1.45 !important;
}

.singleline textarea {
  min-height: 64px !important;
  max-height: 64px !important;
  resize: none !important;
  overflow: hidden !important;
  white-space: nowrap !important;
}

.export-wrap { margin: 28px 40px; }
.export-wrap .stButton > button {
  background: #e6f1a6; color:#000; border:3px solid #000;
  border-radius: 10px; font-weight:800; font-size: 20px; padding: 12px 24px;
}
.export-wrap .stButton > button:disabled { background:#e6e6e6; color:#777; border-color:#999; }

.stDownloadButton > button {
  background: #ffffff; color:#000; border:3px solid #000;
  border-radius: 10px; font-weight:800; font-size: 18px; padding: 10px 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="mock-title">User Story → Testcase Generator</div>', unsafe_allow_html=True)

st.markdown('<div class="mock-label">user story id (optional; needed for evaluation, e.g. US-4)</div>', unsafe_allow_html=True)
us_id = st.text_input(
    "",
    key="us_id_input",
    label_visibility="collapsed",
    placeholder="US-4 (optional)",
    value=""
)

st.markdown('<div class="mock-label">enter your user story here</div>', unsafe_allow_html=True)
st.markdown('<div class="field-single singleline">', unsafe_allow_html=True)
user_story = st.text_area(
    "", key="us_one", label_visibility="hidden",
    placeholder="As a <role>, I want ..., so that ...",
    height=200
)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="mock-label">enter the acceptance criteria (1 criteria per line)</div>', unsafe_allow_html=True)
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
AC_KEYWORDS_PATH = "ac_keywords.json"
BULK_USERSTORIES_PATH = "bulk_userstories.json"

def load_json_file(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

UI_CONTEXT = load_json_file(UI_CONTEXT_PATH, {})
NAV_TARGETS = load_json_file(NAV_TARGETS_PATH, {})
AC_KEYWORDS = load_json_file(AC_KEYWORDS_PATH, {})

st.caption(f"UI context loaded nodes: {len(UI_CONTEXT.get('nodes', [])) if isinstance(UI_CONTEXT, dict) else 0}")
st.caption(f"Navigation targets loaded: {len(NAV_TARGETS) if isinstance(NAV_TARGETS, dict) else 0}")
st.caption(f"AC keyword sets loaded: {len(AC_KEYWORDS) if isinstance(AC_KEYWORDS, dict) else 0}")

# ======================= OPENAI SETUP =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

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
def _json_from_text(txt: str) -> dict:
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```(json)?\s*|\s*```$", "", txt, flags=re.S).strip()
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
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
            model="gpt-5.4-mini",
            temperature=1,
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

CONCEPT_ALIASES = {
    # "new window" removed — not a reliable synonym for popup/modal
    "popup": ["popup", "pop-up", "dialog", "modal", "confirmation pop-up"],
    # "navigate" / "navigated" / "land on" removed — too broad; every step "navigates"
    "redirect": ["redirect", "redirected", "navigated to"],
    "dashboard": ["dashboard"],
    "detail": ["detail", "details"],
    "yes": ["yes", "yes button"],
    "no": ["no", "no button"],
    "delete": ["delete", "deleted", "deletion"],
    "create": ["create", "created", "creation"],
    "edit": ["edit", "edited", "editing"],
    # "shown", "displayed", "present" removed — match virtually every expected-result sentence
    "view": ["view", "visible", "see"],
    # "access denied", "not clickable", "not available" removed — too generic
    "not delete": [
        "not delete", "cannot delete", "can not delete", "unable to delete",
        "no permission to delete", "delete button is not visible",
        "delete button not visible",
    ],
    # "access denied", "not available", "not visible", "button is not present" removed — too generic
    "not create": [
        "not create", "cannot create", "can not create", "unable to create",
        "no permission to create",
    ],
    # "not visible", "not available" removed — match too broadly
    "no access": [
        "no access", "cannot access", "can not access", "access denied", "not accessible",
    ],
    "not view": [
        "not view", "cannot view", "can not view", "unable to view",
        "no permission to view",
    ],
    "not edit": [
        "not edit", "cannot edit", "can not edit", "unable to edit",
        "no permission to edit",
    ],
    "future": ["future", "in the future"],
    # "date format", "format" removed — "format" alone matches anything
    "dd/mm/yyyy": ["dd/mm/yyyy"],
    "button": ["button"],
    "dropdown": ["dropdown", "drop-down", "select"],
    # "according to" removed — too broad
    "filtered": ["filtered", "filter"],
    # "not editable" removed — keep only direct synonyms
    "deactivated": ["deactivated", "disabled", "inactive"],
    "notification": ["notification", "notified"],
    "save": ["save", "saved"],
    "cancel": ["cancel", "cancelled"],
    "appeal": ["appeal"],
    "search": ["search", "search bar", "search button"],
    "reset": ["reset"],
    # "order" removed — appears in nearly every sentence ("in order to", "order of")
    "sorted": ["sorted", "sorted by", "sort by"],
    # "id" removed — substring of "redirect", "dashboard", "valid" etc.
    "ids": ["ids"],
    "50": ["50", "maximum of 50", "up to 50"],
    "200": ["200", "maximum of 200", "up to 200"],
    "300": ["300", "maximum of 300", "up to 300"],
    "500": ["500", "maximum of 500", "up to 500"],
}

def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("„", '"').replace("“", '"').replace("’", "'")
    s = re.sub(r"[^a-z0-9äöüß/\-\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def collect_all_generated_text(cases: List[Dict[str, Any]]) -> str:
    parts = []
    for tc in cases:
        parts.append(tc.get("title", ""))
        for s in tc.get("steps", []) or []:
            parts.append(s.get("step", ""))
            parts.append(s.get("expected", ""))
    return normalize_text(" ".join(parts))



def testcase_full_text(tc: Dict[str, Any]) -> str:
    """Collects title, type, navigation steps, normal steps and expected results."""
    parts = [str(tc.get("title", "")), str(tc.get("type", ""))]
    for key in ["navigation_steps", "steps_only", "steps"]:
        for s in tc.get(key, []) or []:
            if isinstance(s, dict):
                parts.append(str(s.get("step", "")))
                parts.append(str(s.get("expected", "")))
            else:
                parts.append(str(s))
    return normalize_text(" ".join(parts))

def keyword_matches(keyword: str, haystack: str) -> bool:
    keyword = normalize_text(keyword)
    if not keyword:
        return False

    if "|" in keyword:
        return any(keyword_matches(k.strip(), haystack) for k in keyword.split("|"))

    aliases = CONCEPT_ALIASES.get(keyword, [keyword])
    return any(normalize_text(alias) in haystack for alias in aliases)

def evaluate_ac_coverage(us_id_value: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    entries = AC_KEYWORDS.get(us_id_value, [])
    if not entries:
        return {
            "overall_pct": None,
            "covered_count": None,
            "total_count": None,
            "details": [],
            "note": f"No AC keyword set found for {us_id_value}"
        }

    haystack = collect_all_generated_text(cases)
    details = []
    total_score = 0.0

    for entry in entries:
        ac_id = entry.get("ac_id", "")
        keywords = entry.get("keywords", []) or []
        matched = sum(1 for kw in keywords if keyword_matches(kw, haystack))
        score = (matched / len(keywords)) if keywords else 0.0

        details.append({
            "ac_id": ac_id,
            "keywords": keywords,
            "matched": matched,
            "total_keywords": len(keywords),
            "score": round(score, 2)
        })
        total_score += score

    overall_pct = round((total_score / len(entries)) * 100, 2) if entries else None
    covered_count = sum(1 for d in details if d["score"] >= 0.8)

    return {
        "overall_pct": overall_pct,
        "covered_count": covered_count,
        "total_count": len(entries),
        "details": details,
        "note": None
    }


# ======================= LLM-AS-A-JUDGE AC EVALUATION =======================

LLM_JUDGE_SYSTEM_PROMPT = """
You are a QA expert evaluating test coverage.
You receive one acceptance criterion and a set of generated test cases.
Decide whether the test cases adequately cover the acceptance criterion.

Rules:
- Semantic equivalence counts as covered (e.g. "screen is displayed" covers "redirect").
- The criterion does not need to be word-for-word in the test cases.
- If at least one test case addresses the criterion's intent, mark it as covered.
- Return ONLY valid JSON, no markdown, no prose.

Output schema:
{"covered": true | false, "reason": "one sentence explanation"}
"""

def evaluate_ac_coverage_llm(
    us_id_value: str,
    cases: List[Dict[str, Any]],
    ac_blob: str
) -> Dict[str, Any]:
    """
    LLM-as-a-Judge AC coverage evaluation.
    For each acceptance criterion (from ac_blob), calls the LLM to decide
    whether the generated test cases cover it.
    Returns the same shape as evaluate_ac_coverage for easy comparison.
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

    # Build a compact readable representation of the test cases
    tc_text_parts = []
    for tc in cases:
        parts = [f"[{tc.get('id','')}] {tc.get('title','')}"]
        for s in tc.get("steps", []) or []:
            if isinstance(s, dict):
                parts.append(f"  Step: {s.get('step','')}")
                parts.append(f"  Expected: {s.get('expected','')}")
        tc_text_parts.append("\n".join(parts))
    tc_text = "\n\n".join(tc_text_parts)

    details = []
    covered_count = 0

    for idx, ac_line in enumerate(ac_lines, start=1):
        ac_id = f"AC-{idx}"
        payload = {
            "acceptance_criterion": ac_line,
            "generated_test_cases": tc_text
        }
        try:
            resp = client.chat.completions.create(
                model="gpt-5.4-mini",
                temperature=0,
                max_completion_tokens=150,
                messages=[
                    {"role": "system", "content": LLM_JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ]
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw, flags=re.S).strip()
            result = json.loads(raw)
            covered = bool(result.get("covered", False))
            reason = str(result.get("reason", ""))
        except Exception as e:
            covered = False
            reason = f"Judge call failed: {e}"

        if covered:
            covered_count += 1

        details.append({
            "ac_id": ac_id,
            "ac_text": ac_line,
            "covered": covered,
            "reason": reason,
            "score": 1.0 if covered else 0.0
        })

    total = len(ac_lines)
    overall_pct = round((covered_count / total) * 100, 2) if total else None

    return {
        "overall_pct": overall_pct,
        "covered_count": covered_count,
        "total_count": total,
        "details": details,
        "note": None
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


def extract_actual_nav_path(tc: Dict[str, Any]) -> List[str]:
    """
    Extracts a normalized actual navigation path from generated test cases.

    Fix for overlong actual paths:
    - If a step contains a valid explicit ui_node_id, use that ID only.
    - Infer nodes from text only when the step has no valid explicit ui_node_id.
    - This prevents broad text matches like "delete" from adding unrelated SM action,
      TM and TM action delete nodes.
    """
    path: List[str] = []
    valid_ids = _node_ids()

    all_steps: List[Any] = []
    all_steps.extend(tc.get("navigation_steps", []) or [])
    all_steps.extend(tc.get("steps_only", []) or [])

    # Add tc["steps"] only if the source fields above are empty. In normalized
    # with-UI outputs, "steps" already contains navigation_steps + steps_only;
    # adding it again can duplicate evidence and amplify fallback inference.
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

        candidates: List[str] = []

        if explicit and explicit != "LOGIN" and str(explicit) in valid_ids:
            # Explicit model-provided node ID is authoritative for this step.
            candidates.append(str(explicit))
        else:
            # Conservative fallback only when no valid explicit node exists.
            candidates.extend(infer_nodes_from_step_text(step_text, expected_text))

        for node in candidates:
            for expanded in _expand_via_node(node):
                _append_chain(path, expanded)

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


def evaluate_navigation_correctness(us_id_value: str, cases: List[Dict[str, Any]], story: str = "") -> Dict[str, Any]:
    """
    Navigation evaluation with support for the simplified two-level target format.

    Recommended navigation_targets.json format:
      "US-6": {
        "title": "Create Action for SM",
        "required_per_testcase": ["CONSOLE-O", "OPT-SM", "SCR-SM-DETAIL"],
        "required_across_story": ["MOD-SM-ACTION-CREATE", "COMP-SM-ACTION-LIST"]
      }

    Interpretation:
    - required_per_testcase: minimal UI area that every positive/evaluable test case should reach.
    - required_across_story: UI target nodes that should appear at least once across all positive/evaluable
      test cases of the User Story.
    - negative permission/access tests are skipped for Navigation Correctness because they intentionally
      test non-reachability or denied actions.

    Backwards compatibility:
    - also supports the older "targets" format used earlier in the project.
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

    # New two-level target format.
    required_per_testcase = _norm_list(ref.get("required_per_testcase")) if isinstance(ref, dict) else []
    required_across_story = _norm_list(ref.get("required_across_story")) if isinstance(ref, dict) else []
    uses_two_level_format = bool(required_per_testcase or required_across_story)

    # Old formats remain supported.
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
    actual_union: List[str] = []

    def add_to_union(nodes: List[str]):
        for n in nodes:
            if n not in actual_union:
                actual_union.append(n)

    for tc in cases:
        actual = extract_actual_nav_path(tc)
        neg_mode = navigation_negative_mode(tc)

        if uses_two_level_format:

            if neg_mode == "no_access":
                # No-access cases are NOT skipped. They count as correct only if
                # the test explicitly documents the denial/restriction.
                evaluated_cases += 1
                has_denial = _contains_denial_language(tc)
                if has_denial:
                    correct_cases += 1
                details.append({
                    "tc_id": tc.get("id", ""),
                    "actual": actual,
                    "expected": [],
                    "selected_target": "no_access_denial_check",
                    "module_nodes": module_nodes,
                    "can_evaluate": True,
                    "is_correct": has_denial,
                    "module_ok": True,
                    "missing_nodes": [] if has_denial else ["denial language missing"],
                    "forbidden_nodes": [],
                    "forbidden_hit": False,
                    "denial_ok": has_denial,
                    "match_score": 1.0 if has_denial else 0.0,
                    "skip_reason": "" if has_denial else "no_access test missing denial language"
                })
                continue

            required_nodes = required_per_testcase
            selected_target = str(ref.get("title") or "Navigation target")
            if neg_mode == "base_only":
                selected_target = selected_target + " base navigation only"
            forbidden_nodes: List[str] = []
            target = {"label": selected_target, "required_nodes": required_nodes}

        else:
            if neg_mode == "no_access":
                evaluated_cases += 1
                has_denial = _contains_denial_language(tc)
                if has_denial:
                    correct_cases += 1
                details.append({
                    "tc_id": tc.get("id", ""),
                    "actual": actual,
                    "expected": [],
                    "selected_target": "no_access_denial_check",
                    "module_nodes": module_nodes,
                    "can_evaluate": True,
                    "is_correct": has_denial,
                    "module_ok": True,
                    "missing_nodes": [] if has_denial else ["denial language missing"],
                    "forbidden_nodes": [],
                    "forbidden_hit": False,
                    "denial_ok": has_denial,
                    "match_score": 1.0 if has_denial else 0.0,
                    "skip_reason": "" if has_denial else "no_access test missing denial language"
                })
                continue
            if neg_mode == "base_only":
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
                    "denial_ok": True,
                    "match_score": 0.0,
                    "skip_reason": "negative action permission test with old target format"
                })
                continue
            target = _select_best_navigation_target(tc, ref)
            required_nodes = _target_required_nodes(target)
            forbidden_nodes = _target_forbidden_nodes(target)
            selected_target = _target_label(target, ref)

        # Only positive test cases contribute to story-level target coverage.
        # Negative base-only cases often mention denied popups/buttons, so adding
        # their inferred nodes to the union would overstate coverage.
        if neg_mode == "none":
            add_to_union(actual)

        can_evaluate = bool(actual) and bool(required_nodes)
        module_ok = True if not module_nodes else any(m in actual for m in module_nodes)
        required_ok = all(node in actual for node in required_nodes)

        forbidden_hit = any(node in actual for node in forbidden_nodes)
        denial_ok = _target_access_denial_ok(target) and _contains_denial_language(tc)
        forbidden_ok = (not forbidden_hit) or denial_ok

        is_correct = False
        if can_evaluate:
            evaluated_cases += 1
            is_correct = bool(module_ok and required_ok and forbidden_ok)
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
            "match_score": round((len(required_nodes) - len(missing_nodes)) / len(required_nodes), 2) if required_nodes else 0.0,
            "skip_reason": "" if can_evaluate else "No actual navigation nodes extracted or no per-testcase target defined"
        })

    # User-story-level target coverage for the two-level format.
    story_target_total = 0
    story_target_correct = 0
    if uses_two_level_format and required_across_story:
        story_target_total = len(required_across_story)
        story_missing = [node for node in required_across_story if node not in actual_union]
        story_target_correct = story_target_total - len(story_missing)

        details.append({
            "tc_id": "STORY_TARGET_COVERAGE",
            "actual": actual_union,
            "expected": required_across_story,
            "selected_target": "required_across_story",
            "module_nodes": module_nodes,
            "can_evaluate": bool(actual_union),
            "is_correct": len(story_missing) == 0,
            "module_ok": True,
            "missing_nodes": story_missing,
            "forbidden_nodes": [],
            "forbidden_hit": False,
            "denial_ok": False,
            "match_score": round(story_target_correct / story_target_total, 2) if story_target_total else 0.0,
            "skip_reason": ""
        })

    total_evaluated = evaluated_cases + story_target_total
    total_correct = correct_cases + story_target_correct
    correctness_pct = round((total_correct / total_evaluated) * 100, 2) if total_evaluated else None

    if total_evaluated:
        note = None
    elif skipped_cases:
        note = "Only negative permission/access test cases were found; Navigation Correctness was skipped."
    else:
        note = "No evaluable navigation test cases found."

    return {
        "correctness_pct": correctness_pct,
        "correct_count": total_correct,
        "evaluated_count": total_evaluated,
        "testcase_correct_count": correct_cases,
        "testcase_evaluated_count": evaluated_cases,
        "story_target_correct_count": story_target_correct,
        "story_target_total_count": story_target_total,
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

def step_implies_role(step_text: str, expected_text: str, role: str) -> bool:
    combined = normalize_text(f"{step_text} {expected_text}")
    patterns = [
        f"login as {role}",
        f"logged in as {role}",
        f"login with {role}",
        f"log in as {role}",
        f"log in with {role}",
        f"as a {role}",
        f"as {role}",
    ]
    return any(p in combined for p in patterns)

def extract_generated_roles(cases: List[Dict[str, Any]]) -> List[str]:
    found = set()

    for tc in cases:
        for s in tc.get("steps", []) or []:
            step_text = s.get("step", "")
            expected_text = s.get("expected", "")

            for role in ROLE_WORDS:
                if step_implies_role(step_text, expected_text, role):
                    found.add(role)

    return sorted(list(found))

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

def _navigation_not_evaluated_without_ui() -> Dict[str, Any]:
    return {
        "correctness_pct": None,
        "correct_count": None,
        "evaluated_count": None,
        "skipped_count": None,
        "details": [],
        "note": "Navigation Correctness is only evaluated for outputs generated with UI context."
    }


def evaluate_all(
    us_id_value: str,
    story: str,
    ac_blob: str,
    cases: List[Dict[str, Any]],
    use_ui_context: bool = True,
    use_llm_judge: bool = False,
) -> Dict[str, Any]:
    navigation = (
        evaluate_navigation_correctness(us_id_value, cases, story)
        if use_ui_context
        else _navigation_not_evaluated_without_ui()
    )
    ac_llm = (
        evaluate_ac_coverage_llm(us_id_value, cases, ac_blob)
        if use_llm_judge
        else {
            "overall_pct": None, "covered_count": None, "total_count": None,
            "details": [], "note": "LLM judge not enabled."
        }
    )
    return {
        "ac": evaluate_ac_coverage(us_id_value, cases),
        "ac_llm": ac_llm,
        "navigation": navigation,
        "role": evaluate_role_coverage(story, ac_blob, cases)
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


def _metric_or_none(evaluation: Dict[str, Any], section: str, key: str) -> Optional[float]:
    try:
        value = evaluation.get(section, {}).get(key)
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _overall_score(ac_pct: Optional[float], role_pct: Optional[float], nav_pct: Optional[float]) -> Optional[float]:
    """
    Simple combined score for a run.
    It averages all available metric percentages.
    Navigation is often N/A without UI context; in that case it is not included.
    """
    values = [v for v in [ac_pct, role_pct, nav_pct] if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def run_bulk_evaluation(userstories: List[Dict[str, Any]], repetitions: int, use_llm_judge: bool = False) -> pd.DataFrame:
    """
    For every user story and every repetition, run both variants:
    - without UI context
    - with UI context

    Then evaluate each output and return one result row per generated output.
    """
    rows = []
    total_runs = len(userstories) * repetitions * 2
    done = 0

    progress = st.progress(0)
    status = st.empty()

    variants = [
        ("without_ui_context", False),
        ("with_ui_context", True),
    ]

    for rep in range(1, repetitions + 1):
        for item in userstories:
            for variant_name, use_ui in variants:
                done += 1
                status.write(
                    f"Bulk run {done}/{total_runs}: {item['id']} — {variant_name} — repetition {rep}/{repetitions}"
                )
                progress.progress(done / total_runs)

                try:
                    cases, open_q = generate_cases(
                        story=item["story"],
                        ac_blob=item["ac_blob"],
                        use_ui_context=use_ui,
                    )

                    evaluation = evaluate_all(
                        us_id_value=item["id"],
                        story=item["story"],
                        ac_blob=item["ac_blob"],
                        cases=cases,
                        use_ui_context=use_ui,
                        use_llm_judge=use_llm_judge,
                    )

                    ac_pct = _metric_or_none(evaluation, "ac", "overall_pct")
                    ac_llm_pct = _metric_or_none(evaluation, "ac_llm", "overall_pct")
                    role_pct = _metric_or_none(evaluation, "role", "overall_pct")
                    nav_pct = _metric_or_none(evaluation, "navigation", "correctness_pct")

                    rows.append({
                        "repetition": rep,
                        "us_id": item["id"],
                        "title": item.get("title", ""),
                        "variant": variant_name,
                        "use_ui_context": use_ui,
                        "acceptance_criteria_count": item.get("acceptance_criteria_count"),
                        "testcase_count": len(cases),
                        "ac_coverage_pct": ac_pct,
                        "ac_llm_coverage_pct": ac_llm_pct,
                        "role_coverage_pct": role_pct,
                        "navigation_correctness_pct": nav_pct,
                        "overall_score_pct": _overall_score(ac_pct, role_pct, nav_pct),
                        "open_questions_count": len(open_q or []),
                        "error": "",
                    })

                except Exception as e:
                    rows.append({
                        "repetition": rep,
                        "us_id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "variant": variant_name,
                        "use_ui_context": use_ui,
                        "acceptance_criteria_count": item.get("acceptance_criteria_count"),
                        "testcase_count": 0,
                        "ac_coverage_pct": None,
                        "ac_llm_coverage_pct": None,
                        "role_coverage_pct": None,
                        "navigation_correctness_pct": None,
                        "overall_score_pct": None,
                        "open_questions_count": 0,
                        "error": str(e),
                    })

    progress.progress(1.0)
    status.write("Bulk evaluation finished ✅")

    return pd.DataFrame(rows)


def summarize_bulk_results(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return pd.DataFrame()

    agg_dict = dict(
        runs=("variant", "count"),
        user_stories=("us_id", "nunique"),
        avg_testcase_count=("testcase_count", "mean"),
        avg_ac_coverage_pct=("ac_coverage_pct", "mean"),
        std_ac_coverage_pct=("ac_coverage_pct", "std"),
        avg_role_coverage_pct=("role_coverage_pct", "mean"),
        std_role_coverage_pct=("role_coverage_pct", "std"),
        avg_navigation_correctness_pct=("navigation_correctness_pct", "mean"),
        std_navigation_correctness_pct=("navigation_correctness_pct", "std"),
        avg_overall_score_pct=("overall_score_pct", "mean"),
        std_overall_score_pct=("overall_score_pct", "std"),
        failed_runs=("error", lambda values: sum(bool(str(v).strip()) for v in values)),
    )
    if "ac_llm_coverage_pct" in results_df.columns:
        agg_dict["avg_ac_llm_coverage_pct"] = ("ac_llm_coverage_pct", "mean")
        agg_dict["std_ac_llm_coverage_pct"] = ("ac_llm_coverage_pct", "std")

    summary = results_df.groupby("variant", dropna=False).agg(**agg_dict).reset_index()
    return summary.round(2)


def summarize_bulk_by_user_story(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return pd.DataFrame()

    agg_dict = dict(
        runs=("variant", "count"),
        avg_testcase_count=("testcase_count", "mean"),
        avg_ac_coverage_pct=("ac_coverage_pct", "mean"),
        avg_role_coverage_pct=("role_coverage_pct", "mean"),
        avg_navigation_correctness_pct=("navigation_correctness_pct", "mean"),
        avg_overall_score_pct=("overall_score_pct", "mean"),
        failed_runs=("error", lambda values: sum(bool(str(v).strip()) for v in values)),
    )
    if "ac_llm_coverage_pct" in results_df.columns:
        agg_dict["avg_ac_llm_coverage_pct"] = ("ac_llm_coverage_pct", "mean")

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
        nav_corr_value = "N/A" if evaluation["navigation"]["correctness_pct"] is None else f"{evaluation['navigation']['correct_count']}/{evaluation['navigation']['evaluated_count']} ({evaluation['navigation']['correctness_pct']}%)"
        role_value = "N/A" if evaluation["role"]["overall_pct"] is None else f"{evaluation['role']['covered_count']}/{evaluation['role']['total_count']} ({evaluation['role']['overall_pct']}%)"

        rows = [
            ["Metric", "Value"],
            ["AC Coverage", ac_value],
            ["Navigation Correctness", nav_corr_value],
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
    """Renders evaluation metrics and details. Used by all three evaluation sections."""

    def _path_str(node_ids: List[str]) -> str:
        """Converts a list of node IDs to a readable path string with arrows."""
        name_map = _node_name_map()
        names = [name_map.get(nid, nid) for nid in node_ids]
        return " → ".join(names) if names else "—"

    st.subheader(header)

    ac_metric  = "N/A" if ev["ac"]["overall_pct"] is None else f"{ev['ac']['overall_pct']}%"
    nav_metric = "N/A" if ev["navigation"]["correctness_pct"] is None else f"{ev['navigation']['correctness_pct']}%"
    role_metric = "N/A" if ev["role"]["overall_pct"] is None else f"{ev['role']['overall_pct']}%"

    c1, c2, c3 = st.columns(3)
    c1.metric("AC Coverage (Keyword)", ac_metric)
    c2.metric("Navigation Correctness", nav_metric)
    c3.metric("Role Coverage", role_metric)

    ac_llm = ev.get("ac_llm", {})
    if ac_llm.get("overall_pct") is not None:
        st.metric("AC Coverage (LLM Judge)", f"{ac_llm['overall_pct']}%")

    # AC Keyword details
    if ev["ac"].get("note"):
        st.warning(ev["ac"]["note"])
    else:
        st.write(f"**AC Coverage (Keyword):** {ev['ac']['covered_count']}/{ev['ac']['total_count']} ACs mit Score ≥ 0.8")
        with st.expander("Keyword AC details"):
            for d in ev["ac"].get("details", []):
                st.write(f"{d['ac_id']}: score={d['score']} ({d['matched']}/{d['total_keywords']}) keywords={d['keywords']}")

    # AC LLM Judge details
    if ac_llm.get("note") and ac_llm["note"] != "LLM judge not enabled.":
        st.warning(ac_llm["note"])
    elif ac_llm.get("details"):
        st.write(f"**AC Coverage (LLM Judge):** {ac_llm['covered_count']}/{ac_llm['total_count']} ACs covered")
        with st.expander("LLM Judge AC details"):
            for d in ac_llm["details"]:
                icon = "✅" if d["covered"] else "❌"
                st.write(f"{icon} **{d['ac_id']}:** {d['ac_text']}")
                st.caption(f"→ {d['reason']}")

    # Navigation details
    if ev["navigation"].get("note"):
        st.warning(ev["navigation"]["note"])
    else:
        nav = ev["navigation"]
        skipped = nav.get("skipped_count") or 0
        skip_note = f" ({skipped} skipped)" if skipped else ""
        st.write(f"**Navigation Correctness:** {nav['correct_count']}/{nav['evaluated_count']}{skip_note}")
        with st.expander("Navigation details"):
            for d in nav.get("details", []):
                icon = "✅" if d.get("is_correct") else "❌"
                tc_id = d["tc_id"]
                target = d.get("selected_target", "")

                if target == "no_access_denial_check":
                    denial = "denial language present" if d.get("denial_ok") else "⚠️ denial language missing"
                    st.write(f"{icon} **{tc_id}** — no-access test ({denial})")
                elif target == "required_across_story":
                    st.write(f"{icon} **Story-level coverage**")
                    st.caption(f"Expected: {_path_str(d.get('expected', []))}")
                    if d.get("missing_nodes"):
                        name_map = _node_name_map()
                        missing_names = [name_map.get(n, n) for n in d["missing_nodes"]]
                        st.caption(f"Missing: {' → '.join(missing_names)}")
                else:
                    st.write(f"{icon} **{tc_id}** — {target}")
                    st.caption(f"Expected: {_path_str(d.get('expected', []))}")
                    st.caption(f"Actual:   {_path_str(d.get('actual', []))}")
                    if d.get("missing_nodes"):
                        name_map = _node_name_map()
                        missing_names = [name_map.get(n, n) for n in d["missing_nodes"]]
                        st.caption(f"⚠️ Missing: {' → '.join(missing_names)}")

    # Role details
    role = ev["role"]
    st.write(f"**Role Coverage:** {role['covered_count']}/{role['total_count']}")
    st.write(f"Required: {role['required_roles']}  |  Generated: {role['generated_roles']}")
    if role.get("missing_roles"):
        st.warning(f"Missing roles: {role['missing_roles']}")


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
        "export without UI ✨",
        disabled=not (user_story.strip() and ac_text.strip())
    )

with col2:
    clicked_with = st.button(
        "export with UI 🧠✨",
        disabled=not (user_story.strip() and ac_text.strip())
    )

with col3:
    clicked_eval = st.button(
        "evaluate current output 📊",
        disabled=not (bool(st.session_state.last_cases) and us_id.strip())
    )

use_llm_judge_main = st.checkbox(
    "🤖 Also evaluate with LLM-as-a-Judge (uses extra API calls — 1 per AC)",
    value=st.session_state.get("use_llm_judge_main", False),
    key="use_llm_judge_main",
    help="Calls the LLM once per acceptance criterion to semantically judge whether the generated test cases cover it. More accurate than keyword matching, but costs additional API calls."
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
        use_llm_judge=st.session_state.get("use_llm_judge_main", False),
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
    st.success(f"PDF ready ✅ (test cases: {st.session_state.last_cases_count})")
    st.download_button(
        "download PDF 🧾",
        data=st.session_state.last_pdf,
        file_name=f"test_design_{us_id}_{st.session_state.last_variant or 'result'}.pdf",
        mime="application/pdf",
    )




# ======================= SINGLE EXPORT FROM BULK USER STORIES =======================
st.markdown("---")
st.subheader("Single User Story Export 🧾")
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
        "generate single export ✨",
        disabled=not single_us_lookup.strip(),
        key="single_export_button"
    )
with single_btn_col2:
    single_eval_clicked = st.button(
        "evaluate single export 📊",
        disabled=not bool(st.session_state.single_cases),
        key="single_eval_button"
    )

use_llm_judge_single = st.checkbox(
    "🤖 Also evaluate with LLM-as-a-Judge (uses extra API calls — 1 per AC)",
    value=False,
    key="use_llm_judge_single",
    help="Calls the LLM once per acceptance criterion to semantically judge whether the generated test cases cover it."
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
                    use_llm_judge=st.session_state.get("use_llm_judge_single", False),
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
        "download single export PDF 🧾",
        data=st.session_state.single_export_pdf,
        file_name=st.session_state.single_export_filename,
        mime="application/pdf",
        key="single_export_download",
    )


# ======================= BULK EVALUATION UI =======================
st.markdown("---")
st.subheader("Bulk Evaluation 📊")
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

bulk_use_llm_judge = st.checkbox(
    "🤖 Enable LLM-as-a-Judge for AC Coverage in bulk run",
    value=False,
    key="bulk_llm_judge",
    help=(
        "Adds one LLM call per acceptance criterion per run. "
        "Example: 24 user stories × avg 8 ACs × 2 variants × 3 repetitions = ~1,152 extra judge calls. "
        "Enable for a subset of runs or after confirming keyword results first."
    )
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

estimated_calls = len(preview_userstories) * int(bulk_repetitions) * 2
st.caption(f"Estimated LLM calls: {estimated_calls}")

run_bulk_button = st.button(
    "run bulk evaluation 🚀",
    disabled=not (client and preview_userstories),
)

if run_bulk_button:
    try:
        # Reload file so the stream position is correct.
        if bulk_uploaded_file is not None:
            bulk_uploaded_file.seek(0)
            bulk_userstories = load_bulk_userstories(bulk_uploaded_file)
        else:
            bulk_userstories = load_bulk_userstories(BULK_USERSTORIES_PATH)

        with st.spinner("Running bulk evaluation. This may take several minutes..."):
            results_df = run_bulk_evaluation(bulk_userstories, int(bulk_repetitions), use_llm_judge=bulk_use_llm_judge)
            summary_df = summarize_bulk_results(results_df)
            by_us_df = summarize_bulk_by_user_story(results_df)

        st.session_state.bulk_results_df = results_df
        st.session_state.bulk_summary_df = summary_df
        st.session_state.bulk_by_us_df = by_us_df

    except Exception as e:
        st.error(f"Bulk evaluation failed: {e}")

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

    st.markdown("### Variant comparison")
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("#### With UI Context")
        if with_ui is not None:
            st.metric("AC Coverage (Keyword)", _fmt_pct(with_ui["avg_ac_coverage_pct"]))
            if "avg_ac_llm_coverage_pct" in with_ui.index:
                st.metric("AC Coverage (LLM Judge)", _fmt_pct(with_ui["avg_ac_llm_coverage_pct"]))
            st.metric("Role Coverage", _fmt_pct(with_ui["avg_role_coverage_pct"]))
            st.metric("Navigation Correctness", _fmt_pct(with_ui["avg_navigation_correctness_pct"]))
            st.metric("Overall Score", _fmt_pct(with_ui["avg_overall_score_pct"]))
        else:
            st.warning("No results for with_ui_context.")

    with right_col:
        st.markdown("#### Without UI Context")
        if without_ui is not None:
            st.metric("AC Coverage (Keyword)", _fmt_pct(without_ui["avg_ac_coverage_pct"]))
            if "avg_ac_llm_coverage_pct" in without_ui.index:
                st.metric("AC Coverage (LLM Judge)", _fmt_pct(without_ui["avg_ac_llm_coverage_pct"]))
            st.metric("Role Coverage", _fmt_pct(without_ui["avg_role_coverage_pct"]))
            st.metric("Navigation Correctness", _fmt_pct(without_ui["avg_navigation_correctness_pct"]))
            st.metric("Overall Score", _fmt_pct(without_ui["avg_overall_score_pct"]))
        else:
            st.warning("No results for without_ui_context.")

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
