# app.py
# Run:
#   pip install streamlit python-dotenv reportlab openai
#   streamlit run app.py

import os
import io
import json
import re
from typing import Dict, List, Any, Tuple, Set

import streamlit as st
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

html, body, .stApp, .stMarkdown, .stAlert, .stDataFrame, .stForm,
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

st.markdown('<div class="mock-label">user story id</div>', unsafe_allow_html=True)
us_id = st.text_input(
    "",
    key="us_id_input",
    value="US-1",
    placeholder="US-1",
    label_visibility="collapsed"
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

# ======================= LOADERS =======================
UI_CONTEXT_PATH = "ui_context.json"
NAV_REFERENCE_PATH = "navigation_reference.json"

def load_ui_context(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            ctx = json.load(f)
        if not isinstance(ctx.get("nodes", None), list):
            return {}
        if not isinstance(ctx.get("relationships", []), list):
            ctx["relationships"] = []
        return ctx
    except Exception as e:
        st.warning(f"UI context could not be loaded: {e}")
        return {}

def load_navigation_reference(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        st.warning("navigation_reference.json must contain a JSON list.")
        return []
    except Exception as e:
        st.warning(f"Navigation reference could not be loaded: {e}")
        return []

UI_CONTEXT = load_ui_context(UI_CONTEXT_PATH)
NAV_REFERENCE = load_navigation_reference(NAV_REFERENCE_PATH)

st.caption(f"UI context loaded nodes: {len(UI_CONTEXT.get('nodes', []))}")
st.caption(f"Navigation references loaded: {len(NAV_REFERENCE)}")

# ======================= OPENAI SETUP =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

SYSTEM_PROMPT_WITH_UI = """
You are a senior test engineer.
Return ONLY valid JSON. No markdown. No prose.

You receive:
- a user story
- acceptance criteria
- ui_context with node IDs

STRICT RULES:
- Do NOT invent UI nodes that are not present in ui_context.nodes.
- For each test case, provide a machine-readable "navigation_path" using ONLY node IDs from ui_context.
- "navigation_path" must be an ordered list of node IDs that represents the intended navigation for the test case.
- Keep real test actions in "steps". Do NOT replace real test actions with generic navigation text.
- A requirement may only appear in "covers" if the test case actually tests it.

TRACEABILITY RULES:
- Copy every acceptance criterion EXACTLY into "requirements".
- Each test case MUST include a "covers" array with requirement IDs it truly covers.
- It is allowed that a test case covers multiple requirements.
- It is allowed that some requirements stay uncovered if you cannot test them properly.

OUTPUT SCHEMA:
{
  "requirements": [
    {"id":"REQ-1","text":"exact acceptance criterion text"}
  ],
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional|Negative|Boundary",
      "covers":["REQ-1"],
      "navigation_path":["CONSOLE-D","OPT-MM","SCR-MM-DASHBOARD","SCR-MM-DETAIL"],
      "steps":[
        {"step":"string","expected":"string"}
      ]
    }
  ],
  "open_questions":[]
}
"""

SYSTEM_PROMPT_NO_UI = """
You are a senior test engineer.
Return ONLY valid JSON. No markdown. No prose.

Generate test cases from the user story and acceptance criteria only.

STRICT RULES:
- Keep real test action steps.
- A requirement may only appear in "covers" if the test case actually tests it.

TRACEABILITY RULES:
- Copy every acceptance criterion EXACTLY into "requirements".
- Each test case MUST include a "covers" array with requirement IDs it truly covers.

OUTPUT SCHEMA:
{
  "requirements": [
    {"id":"REQ-1","text":"exact acceptance criterion text"}
  ],
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional|Negative|Boundary",
      "covers":["REQ-1"],
      "steps":[
        {"step":"string","expected":"string"}
      ]
    }
  ],
  "open_questions":[]
}
"""

ROLE_NAMES = ["director", "manager", "agent"]

# ======================= HELPERS =======================
def _clean_line(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^[•\-\*\d\.\)\( ]+", "", s).strip()
    return s

def _ac_lines(ac_blob: str) -> List[str]:
    return [_clean_line(l) for l in ac_blob.splitlines() if _clean_line(l)]

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
    return {
        "requirements": [],
        "test_cases": [],
        "open_questions": ["Model response was not valid JSON."]
    }

def _normalize_step(step_obj):
    if isinstance(step_obj, dict):
        return {
            "step": (step_obj.get("step", "") or "").strip(),
            "expected": (step_obj.get("expected", "") or "").strip(),
        }
    return {"step": str(step_obj), "expected": ""}

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

def _build_requirements_from_ac(ac_blob: str) -> List[Dict[str, str]]:
    lines = _ac_lines(ac_blob)
    return [{"id": f"REQ-{i}", "text": ac} for i, ac in enumerate(lines, start=1)]

def _normalize_requirements(raw_requirements: List[Dict[str, Any]], ac_blob: str) -> List[Dict[str, str]]:
    fallback = _build_requirements_from_ac(ac_blob)
    if not raw_requirements:
        return fallback

    cleaned = []
    for i, req in enumerate(raw_requirements, start=1):
        req_id = str(req.get("id", f"REQ-{i}")).strip() or f"REQ-{i}"
        text = _clean_line(req.get("text", ""))
        if text:
            cleaned.append({"id": req_id, "text": text})

    ac_lines = _ac_lines(ac_blob)
    if len(cleaned) != len(ac_lines):
        return fallback

    return cleaned if cleaned else fallback

def _keep_only_valid_covers(test_cases: List[Dict[str, Any]], requirements: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    valid_req_ids = {r["id"] for r in requirements}
    fixed = []

    for tc in test_cases:
        covers = tc.get("covers", []) or []
        covers = [c for c in covers if c in valid_req_ids]
        tc["covers"] = covers
        fixed.append(tc)

    return fixed

def _normalize_navigation_path(path: Any, ui_context: Dict[str, Any]) -> List[str]:
    if not isinstance(path, list):
        return []

    valid_nodes = {n["id"] for n in ui_context.get("nodes", [])}
    cleaned = []
    for node_id in path:
        node_id = str(node_id).strip()
        if node_id in valid_nodes:
            if not cleaned or cleaned[-1] != node_id:
                cleaned.append(node_id)
    return cleaned

def _normalize_test_cases(tcs: List[Dict[str, Any]], use_ui_context: bool, ui_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    fixed = []

    for tc in tcs:
        steps = [_normalize_step(s) for s in (tc.get("steps", []) or [])]
        steps = [
            s for s in steps
            if (s.get("step") or "").strip() not in {"", "—"}
               or (s.get("expected") or "").strip() not in {"", "—"}
        ]

        navigation_path = _normalize_navigation_path(tc.get("navigation_path", []), ui_context) if use_ui_context else []

        fixed.append(
            {
                "id": (tc.get("id", "") or "").strip(),
                "title": (tc.get("title", "") or "").strip(),
                "priority": (tc.get("priority", "") or "").strip(),
                "type": (tc.get("type", "") or "").strip(),
                "covers": tc.get("covers", []) or [],
                "navigation_path": navigation_path,
                "steps": steps,
            }
        )

    return fixed

def _find_reference_for_us(us_id_value: str, nav_reference: List[Dict[str, Any]]) -> Dict[str, Any]:
    us_id_value = (us_id_value or "").strip().lower()
    for item in nav_reference:
        if str(item.get("us_id", "")).strip().lower() == us_id_value:
            return item
    return {}

# ======================= GENERATION =======================
def generate_cases(story: str, ac_blob: str, use_ui_context: bool = True):
    if not client:
        return {
            "requirements": _build_requirements_from_ac(ac_blob),
            "test_cases": [],
            "open_questions": ["OpenAI client not initialized (missing OPENAI_API_KEY or openai package)."]
        }

    if not story.strip():
        return {
            "requirements": _build_requirements_from_ac(ac_blob),
            "test_cases": [],
            "open_questions": ["User story is empty."]
        }

    payload = {
        "story": story.strip(),
        "acceptance_criteria": _ac_lines(ac_blob),
    }

    system_prompt = SYSTEM_PROMPT_WITH_UI if use_ui_context else SYSTEM_PROMPT_NO_UI
    if use_ui_context:
        payload["ui_context"] = UI_CONTEXT

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        data = _json_from_text(resp.choices[0].message.content)

        requirements = _normalize_requirements(data.get("requirements", []) or [], ac_blob)
        raw_open_q = data.get("open_questions", []) or []
        tcs = data.get("test_cases", []) or []
        open_q = _clean_open_questions(raw_open_q)

        fixed = _normalize_test_cases(tcs, use_ui_context, UI_CONTEXT)
        fixed = _keep_only_valid_covers(fixed, requirements)

        return {
            "requirements": requirements,
            "test_cases": fixed,
            "open_questions": open_q,
        }

    except Exception as e:
        return {
            "requirements": _build_requirements_from_ac(ac_blob),
            "test_cases": [],
            "open_questions": [f"OpenAI call failed: {e}"]
        }

# ======================= EVALUATION =======================
def _lower_text_block_from_case(tc: Dict[str, Any]) -> str:
    parts = [tc.get("title", "") or ""]
    for s in tc.get("steps", []) or []:
        parts.append(s.get("step", "") or "")
        parts.append(s.get("expected", "") or "")
    return " ".join(parts).lower()

def _extract_roles_from_text(text: str) -> Set[str]:
    t = (text or "").lower()
    return {role for role in ROLE_NAMES if role in t}

def _extract_roles_from_requirements(story: str, requirements: List[Dict[str, str]]) -> Set[str]:
    found = _extract_roles_from_text(story)
    for req in requirements:
        found |= _extract_roles_from_text(req.get("text", ""))
    return found

def _calc_role_coverage(story: str, requirements: List[Dict[str, str]], test_cases: List[Dict[str, Any]]) -> Tuple[int, int, float, List[str]]:
    required_roles = _extract_roles_from_requirements(story, requirements)
    tested_roles = set()

    for tc in test_cases:
        tested_roles |= _extract_roles_from_text(_lower_text_block_from_case(tc))

    covered = len(required_roles & tested_roles)
    total = len(required_roles)
    pct = round((covered / total) * 100, 2) if total else 0.0
    missing = sorted(list(required_roles - tested_roles))
    return covered, total, pct, missing

def _calc_traceability_completeness(test_cases: List[Dict[str, Any]]) -> Tuple[int, int, float]:
    total = len(test_cases)
    with_covers = sum(1 for tc in test_cases if tc.get("covers"))
    pct = round((with_covers / total) * 100, 2) if total else 0.0
    return with_covers, total, pct

def _calc_ac_coverage(requirements: List[Dict[str, str]], test_cases: List[Dict[str, Any]]) -> Tuple[int, int, float, List[str], List[str]]:
    req_ids = {r["id"] for r in requirements}
    covered_ids = set()

    for tc in test_cases:
        for req_id in tc.get("covers", []) or []:
            if req_id in req_ids:
                covered_ids.add(req_id)

    missing_ids = []
    missing_texts = []
    for req in requirements:
        if req["id"] not in covered_ids:
            missing_ids.append(req["id"])
            missing_texts.append(req["text"])

    covered = len(covered_ids)
    total = len(req_ids)
    pct = round((covered / total) * 100, 2) if total else 0.0
    return covered, total, pct, missing_ids, missing_texts

def _calc_navigation_path_match(
    us_id_value: str,
    test_cases: List[Dict[str, Any]],
    nav_reference: List[Dict[str, Any]],
    use_ui: bool
) -> Tuple[Any, Any, Any, List[str], List[Dict[str, Any]], bool]:
    if not use_ui:
        return None, None, None, [], [], False

    ref = _find_reference_for_us(us_id_value, nav_reference)
    expected = ref.get("expected_navigation", []) or []
    if not expected:
        return None, None, None, [f"No navigation reference found for {us_id_value}"], [], False

    evaluable_cases = [tc for tc in test_cases if tc.get("navigation_path")]
    if not evaluable_cases:
        return None, None, None, ["No test case contains a machine-readable navigation_path."], [], False

    matched = 0
    comparisons = 0
    mismatches = []
    case_details = []

    for tc in evaluable_cases:
        actual = tc.get("navigation_path", [])
        compare_len = min(len(expected), len(actual))
        local_match = 0

        for i in range(compare_len):
            comparisons += 1
            if expected[i] == actual[i]:
                matched += 1
                local_match += 1
            else:
                mismatches.append(f"{tc.get('id','')}: expected {expected[i]} but got {actual[i]} at position {i+1}")

        if len(actual) < len(expected):
            for i in range(len(actual), len(expected)):
                comparisons += 1
                mismatches.append(f"{tc.get('id','')}: missing expected node {expected[i]} at position {i+1}")

        if len(actual) > len(expected):
            for i in range(len(expected), len(actual)):
                comparisons += 1
                mismatches.append(f"{tc.get('id','')}: unexpected extra node {actual[i]} at position {i+1}")

        case_details.append({
            "test_case_id": tc.get("id", ""),
            "actual_path": actual,
            "matched_prefix_items": local_match,
        })

    pct = round((matched / comparisons) * 100, 2) if comparisons else 0.0
    return matched, comparisons, pct, mismatches[:10], case_details, True

def evaluate_result(
    us_id_value: str,
    story: str,
    raw_result: Dict[str, Any],
    nav_reference: List[Dict[str, Any]],
    use_ui: bool
) -> Dict[str, Any]:
    requirements = raw_result.get("requirements", []) or []
    test_cases = raw_result.get("test_cases", []) or []

    ac_cov_num, ac_cov_den, ac_cov_pct, missing_req_ids, missing_req_texts = _calc_ac_coverage(requirements, test_cases)
    role_num, role_den, role_pct, missing_roles = _calc_role_coverage(story, requirements, test_cases)
    trace_num, trace_den, trace_pct = _calc_traceability_completeness(test_cases)
    path_num, path_den, path_pct, path_mismatches, case_paths, path_evaluable = _calc_navigation_path_match(
        us_id_value, test_cases, nav_reference, use_ui
    )

    return {
        "ac_coverage_num": ac_cov_num,
        "ac_coverage_den": ac_cov_den,
        "ac_coverage_pct": ac_cov_pct,
        "role_coverage_num": role_num,
        "role_coverage_den": role_den,
        "role_coverage_pct": role_pct,
        "traceability_num": trace_num,
        "traceability_den": trace_den,
        "traceability_pct": trace_pct,
        "path_match_num": path_num,
        "path_match_den": path_den,
        "path_match_pct": path_pct,
        "path_match_evaluable": path_evaluable,
        "missing_req_ids": missing_req_ids,
        "missing_req_texts": missing_req_texts,
        "missing_roles": missing_roles,
        "path_mismatches": path_mismatches,
        "case_paths": case_paths,
        "test_case_count": len(test_cases),
    }

# ======================= PDF BUILDER =======================
def build_pdf(
    story_text: str,
    ac_blob: str,
    cases: list,
    open_questions: list,
    evaluation: Dict[str, Any] = None,
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
    lines = _ac_lines(ac_blob)
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
        path_value = "N/A"
        if evaluation.get("path_match_evaluable"):
            path_value = f"{evaluation.get('path_match_num', 0)}/{evaluation.get('path_match_den', 0)} ({evaluation.get('path_match_pct', 0)}%)"

        erows = [
            ["Metric", "Value"],
            ["AC Coverage", f"{evaluation.get('ac_coverage_num', 0)}/{evaluation.get('ac_coverage_den', 0)} ({evaluation.get('ac_coverage_pct', 0)}%)"],
            ["Traceability Completeness", f"{evaluation.get('traceability_num', 0)}/{evaluation.get('traceability_den', 0)} ({evaluation.get('traceability_pct', 0)}%)"],
            ["Role Coverage", f"{evaluation.get('role_coverage_num', 0)}/{evaluation.get('role_coverage_den', 0)} ({evaluation.get('role_coverage_pct', 0)}%)"],
            ["Navigation Path Match", path_value],
            ["Test Cases", str(evaluation.get('test_case_count', 0))],
        ]
        et = Table(erows, colWidths=[180, 260])
        et.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        flow.append(et)
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

        trows = [["ID", "Title", "Priority", "Type", "Covers"]]
        for tc in cases:
            trows.append(
                [
                    Paragraph(tc.get("id", "") or "", cell),
                    Paragraph(tc.get("title", "") or "", cell),
                    Paragraph(tc.get("priority", "") or "", cell),
                    Paragraph(tc.get("type", "") or "", cell),
                    Paragraph(", ".join(tc.get("covers", []) or []) or "—", cell),
                ]
            )

        t = Table(trows, colWidths=[45, 235, 55, 55, 100])
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

            nav_path = tc.get("navigation_path", []) or []
            flow.append(Paragraph(f"<b>Navigation Path:</b> {' → '.join(nav_path) if nav_path else 'N/A'}", body))
            flow.append(Spacer(1, 4))

            steps = tc.get("steps", []) or []

            step_rows = [
                [
                    Paragraph("Step", styles["Heading5"]),
                    Paragraph("Action", styles["Heading5"]),
                    Paragraph("Expected Result", styles["Heading5"]),
                ]
            ]

            if steps:
                for i, s in enumerate(steps, start=1):
                    step_rows.append(
                        [
                            Paragraph(str(i), cell),
                            Paragraph(s.get("step", "") or "—", cell),
                            Paragraph(s.get("expected", "") or "—", cell),
                        ]
                    )
            else:
                step_rows.append(
                    [
                        Paragraph("1", cell),
                        Paragraph("No steps generated.", cell),
                        Paragraph("Review prompt/model output.", cell),
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

# ======================= SESSION STATE =======================
if "last_pdf" not in st.session_state:
    st.session_state.last_pdf = None
if "last_open_questions" not in st.session_state:
    st.session_state.last_open_questions = []
if "last_cases_count" not in st.session_state:
    st.session_state.last_cases_count = 0
if "last_variant" not in st.session_state:
    st.session_state.last_variant = None
if "last_raw_result" not in st.session_state:
    st.session_state.last_raw_result = None
if "last_evaluation" not in st.session_state:
    st.session_state.last_evaluation = None
if "last_use_ui" not in st.session_state:
    st.session_state.last_use_ui = False

# ======================= ACTIONS =======================
st.markdown('<div class="export-wrap">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    clicked_without = st.button(
        "export without UI ✨",
        disabled=not (us_id.strip() and user_story.strip() and ac_text.strip())
    )

with col2:
    clicked_with = st.button(
        "export with UI 🧠✨",
        disabled=not (us_id.strip() and user_story.strip() and ac_text.strip())
    )

with col3:
    clicked_evaluate = st.button(
        "evaluate output 📊",
        disabled=not bool(st.session_state.last_raw_result)
    )

st.markdown('</div>', unsafe_allow_html=True)

if clicked_without or clicked_with:
    use_ui = clicked_with

    with st.spinner("Generating test cases and building PDF..."):
        result = generate_cases(user_story, ac_text, use_ui_context=use_ui)
        cases = result.get("test_cases", []) or []
        open_q = result.get("open_questions", []) or []

        st.session_state.last_raw_result = result
        st.session_state.last_open_questions = open_q
        st.session_state.last_cases_count = len(cases)
        st.session_state.last_variant = "with_ui_context" if use_ui else "without_ui_context"
        st.session_state.last_use_ui = use_ui
        st.session_state.last_evaluation = None

        pdf_bytes = build_pdf(
            user_story,
            ac_text,
            cases,
            open_q,
            evaluation=None,
            us_id_value=us_id
        )
        st.session_state.last_pdf = pdf_bytes

if clicked_evaluate and st.session_state.last_raw_result:
    with st.spinner("Evaluating generated design..."):
        evaluation = evaluate_result(
            us_id_value=us_id,
            story=user_story,
            raw_result=st.session_state.last_raw_result,
            nav_reference=NAV_REFERENCE,
            use_ui=st.session_state.last_use_ui,
        )
        st.session_state.last_evaluation = evaluation

        cases = st.session_state.last_raw_result.get("test_cases", []) or []
        open_q = st.session_state.last_open_questions or []
        pdf_bytes = build_pdf(
            user_story,
            ac_text,
            cases,
            open_q,
            evaluation=evaluation,
            us_id_value=us_id
        )
        st.session_state.last_pdf = pdf_bytes

# ======================= OUTPUT =======================
if st.session_state.last_variant:
    st.info(f"Generated with: {st.session_state.last_variant}")

if st.session_state.last_open_questions:
    cleaned_open_questions = _clean_open_questions(st.session_state.last_open_questions)
    st.warning("Notes / Open Questions:\n- " + "\n- ".join(cleaned_open_questions))

if st.session_state.last_raw_result:
    st.subheader("Requirement Mapping")
    reqs = st.session_state.last_raw_result.get("requirements", []) or []
    tcs = st.session_state.last_raw_result.get("test_cases", []) or []

    for req in reqs:
        st.write(f"**{req['id']}**: {req['text']}")

    st.write("---")

    for tc in tcs:
        st.write(f"**{tc.get('id','')}** covers: {', '.join(tc.get('covers', []) or []) or '—'}")
        st.write(f"Path: {' -> '.join(tc.get('navigation_path', []) or []) or 'N/A'}")

if st.session_state.last_evaluation:
    ev = st.session_state.last_evaluation
    st.subheader("Automated Evaluation")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AC Coverage", f"{ev['ac_coverage_pct']}%")
    m2.metric("Traceability", f"{ev['traceability_pct']}%")
    m3.metric("Role Coverage", f"{ev['role_coverage_pct']}%")
    m4.metric("Path Match", "N/A" if not ev["path_match_evaluable"] else f"{ev['path_match_pct']}%")

    st.write(f"**AC Coverage:** {ev['ac_coverage_num']}/{ev['ac_coverage_den']}")
    st.write(f"**Traceability Completeness:** {ev['traceability_num']}/{ev['traceability_den']}")
    st.write(f"**Role Coverage:** {ev['role_coverage_num']}/{ev['role_coverage_den']}")

    if st.session_state.last_use_ui:
        if ev["path_match_evaluable"]:
            st.write(f"**Navigation Path Match:** {ev['path_match_num']}/{ev['path_match_den']}")
        else:
            st.write("**Navigation Path Match:** N/A")
    else:
        st.write("**Navigation Path Match:** not applicable for generation without UI context")

    if ev.get("missing_roles"):
        st.error("Missing roles in generated tests: " + ", ".join(ev["missing_roles"]))

    if ev.get("missing_req_texts"):
        st.error("Uncovered requirements:")
        for req_id, req_text in zip(ev["missing_req_ids"], ev["missing_req_texts"]):
            st.write(f"- {req_id}: {req_text}")
    else:
        st.success("All explicitly mapped requirements are covered.")

    if ev.get("path_mismatches"):
        st.warning("Navigation path mismatches / notes:")
        for item in ev["path_mismatches"]:
            st.write(f"- {item}")

    if ev.get("case_paths"):
        st.subheader("Actual Paths per Test Case")
        for cp in ev["case_paths"]:
            st.write(f"**{cp['test_case_id']}**: {' -> '.join(cp['actual_path']) if cp['actual_path'] else 'N/A'}")

if st.session_state.last_pdf:
    st.success(f"PDF ready ✅ (test cases: {st.session_state.last_cases_count})")
    st.download_button(
        "download PDF 🧾",
        data=st.session_state.last_pdf,
        file_name=f"test_design_{us_id}_{st.session_state.last_variant or 'result'}.pdf",
        mime="application/pdf",
    )
