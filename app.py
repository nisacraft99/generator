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

st.markdown('<div class="mock-label">user story id (z. B. US-4)</div>', unsafe_allow_html=True)
us_id = st.text_input(
    "", key="us_id_input", label_visibility="collapsed", placeholder="US-4", value="US-4"
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
NAV_REFERENCE_PATH = "navigation_reference.json"
AC_KEYWORDS_PATH = "ac_keywords.json"

def load_json_file(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

UI_CONTEXT = load_json_file(UI_CONTEXT_PATH, {})
NAV_REFERENCE = load_json_file(NAV_REFERENCE_PATH, [])
AC_KEYWORDS = load_json_file(AC_KEYWORDS_PATH, {})

st.caption(f"UI context loaded nodes: {len(UI_CONTEXT.get('nodes', [])) if isinstance(UI_CONTEXT, dict) else 0}")
st.caption(f"Navigation references loaded: {len(NAV_REFERENCE) if isinstance(NAV_REFERENCE, list) else 0}")
st.caption(f"AC keyword sets loaded: {len(AC_KEYWORDS) if isinstance(AC_KEYWORDS, dict) else 0}")

# ======================= OPENAI SETUP =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

SYSTEM_PROMPT_WITH_UI = """
You are a senior test engineer.
Return ONLY valid JSON (no markdown, no prose).

You may receive a UI structure as 'ui_context' (JSON with nodes and relationships).
If ui_context is provided, you MUST use it to generate concrete navigation.

STRICT UI RULES (MANDATORY):
- Do NOT invent menus/screens/buttons/fields that are not present in ui_context.nodes.
- Every navigation step SHOULD include 'ui_node_id' that matches an existing ui_context.nodes[].id when possible.
- Navigation must be explicit and beginner-friendly.
- Generic steps like "Navigate to X" are NOT allowed if ui_context provides the path elements.

TEST CASE GRANULARITY RULES:
- Prefer one focused test case per acceptance criterion.
- Do NOT merge many acceptance criteria into one test case.
- Keep negative role tests separate from positive functional tests.
- Keep navigation and test logic in the same testcase output, with navigation first and then feature steps.

COVERAGE IS THE TOP PRIORITY:
- Every acceptance criterion MUST be covered explicitly in the testcase set.
- The test cases must cover all roles mentioned in the user story and acceptance criteria.
- If needed, create additional test cases to cover uncovered acceptance criteria.

ROLE AND OWNERSHIP RULES:
- Role mention does NOT imply role-owned navigation.
- If a feature belongs to a specific console/module, all navigation must follow that feature's owning console.
- Manager Meeting (MM) belongs to Director Console.
- Agent Meeting (AM) belongs to Manager Console.
- A manager negative test for MM may log in as Manager, but must not invent a Manager Console path to MM if such a path does not exist.
- For negative permission tests, do not replace the generated role with a fallback role.
- If a user has viewing permission but not create/edit/delete permission, test the missing control or denied action, not full module denial.

NAVIGATION IS STRONGLY PREFERRED:
For EVERY test case with ui_context, try to include:
- FIRST navigation step = login
- SECOND navigation step = console node
- THIRD navigation step = nav_option node
- FOURTH navigation step = screen node

OUTPUT SCHEMA:
{
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional|Negative|Boundary",
      "navigation_steps":[
        {"step":"string","expected":"string","ui_node_id":"string"}
      ],
      "steps":[
        {"step":"string","expected":"string","ui_node_id":"string"}
      ]
    }
  ],
  "open_questions":[]
}
"""

SYSTEM_PROMPT_NO_UI = """
You are a senior test engineer.
Return ONLY valid JSON (no markdown, no prose).

Generate test cases based ONLY on the provided user story and acceptance criteria.

IMPORTANT RULES:
- Do NOT assume any UI structure.
- Do NOT invent menus, screens, consoles, dashboards, popups, or navigation paths.
- Do NOT include ui_node_id values.
- Focus on functional behavior derived from the requirements only.
- Prefer one focused test case per acceptance criterion.
- Do NOT merge many acceptance criteria into one test case.
- Keep negative role tests separate from positive functional tests.

OUTPUT SCHEMA:
{
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional|Negative|Boundary",
      "steps":[
        {"step":"string","expected":"string","ui_node_id":null}
      ]
    }
  ],
  "open_questions":[]
}
"""

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
            model="gpt-5.4",
            temperature=0.2,
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

            merged_steps = nav + steps if use_ui_context else steps
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
    "popup": ["popup", "pop-up", "dialog", "modal", "confirmation pop-up", "new window"],
    "redirect": ["redirect", "redirected", "navigated", "navigate", "navigated to", "land on"],
    "dashboard": ["dashboard"],
    "detail": ["detail", "details"],
    "yes": ["yes", "yes button"],
    "no": ["no", "no button"],
    "delete": ["delete", "deleted", "deletion"],
    "create": ["create", "created", "creation"],
    "edit": ["edit", "edited", "editing"],
    "view": ["view", "visible", "see", "shown", "displayed", "present"],
    "not delete": [
        "not delete", "cannot delete", "can not delete", "unable to delete",
        "no permission to delete", "delete button is not visible",
        "delete button not visible", "delete button is not functional",
        "access denied", "not clickable", "not available"
    ],
    "not create": [
        "not create", "cannot create", "can not create", "unable to create",
        "no permission to create", "access denied", "not available", "not visible",
        "button is not present", "button not present"
    ],
    "no access": [
        "no access", "cannot access", "can not access", "access denied",
        "not visible", "not available"
    ],
    "future": ["future", "in the future"],
    "dd/mm/yyyy": ["dd/mm/yyyy", "date format", "format"],
    "button": ["button"],
    "dropdown": ["dropdown", "drop-down", "select"],
    "filtered": ["filtered", "filter", "according to"],
    "deactivated": ["deactivated", "disabled", "not editable", "inactive"],
    "notification": ["notification", "notified"],
    "save": ["save", "saved"],
    "cancel": ["cancel", "cancelled"],
    "appeal": ["appeal"],
    "search": ["search", "search bar", "search button"],
    "reset": ["reset"],
    "sorted": ["sorted", "order"],
    "ids": ["id", "ids"],
    "50": ["50", "maximum of 50", "up to 50"],
    "200": ["200", "maximum of 200", "up to 200"],
    "300": ["300", "maximum of 300", "up to 300"],
    "500": ["500", "maximum of 500", "up to 500"]
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

def find_nav_reference(us_id_value: str) -> Optional[Dict[str, Any]]:
    for item in NAV_REFERENCE:
        if str(item.get("us_id", "")).strip().lower() == us_id_value.strip().lower():
            return item
    return None

def infer_node_from_step_text(step_text: str, expected_text: str) -> Optional[str]:
    text = normalize_text(f"{step_text} {expected_text}")

    if "director console" in text:
        return "CONSOLE-D"
    if "manager console" in text:
        return "CONSOLE-M"
    if "calendar console" in text:
        return "CONSOLE-C"
    if "evaluation console" in text:
        return "CONSOLE-E"

    if "manager meeting" in text or "manager meetings" in text:
        return "OPT-MM"
    if "agent meeting" in text or "agent meetings" in text:
        return "OPT-AM"
    if "calendar view" in text or ("calendar" in text and "option" in text):
        return "OPT-CALENDAR"
    if "evaluate employees" in text:
        return "OPT-EVALUATE"

    if "mm dashboard" in text:
        return "SCR-MM-DASHBOARD"
    if "am dashboard" in text:
        return "SCR-AM-DASHBOARD"
    if "mm detail" in text or "existing mm id" in text or "open an existing mm" in text:
        return "SCR-MM-DETAIL"
    if "am detail" in text or "existing am id" in text or "open an existing am" in text:
        return "SCR-AM-DETAIL"
    if "calendar" in text and "displayed" in text:
        return "SCR-CALENDAR"
    if "evaluate employees dashboard" in text:
        return "SCR-EVALUATE-DASHBOARD"

    return None

def extract_actual_nav_path(tc: Dict[str, Any]) -> List[str]:
    path = []

    # 1) ui_node_id aus navigation_steps
    for s in tc.get("navigation_steps", []) or []:
        node = s.get("ui_node_id")
        if node and node != "LOGIN":
            path.append(node)

    # 2) fallback: navigation_steps Text
    if not path:
        for s in tc.get("navigation_steps", []) or []:
            inferred = infer_node_from_step_text(
                s.get("step", ""),
                s.get("expected", "")
            )
            if inferred:
                path.append(inferred)

    # 3) fallback: erste steps
    if not path:
        for s in (tc.get("steps", []) or [])[:6]:
            inferred = infer_node_from_step_text(
                s.get("step", ""),
                s.get("expected", "")
            )
            if inferred:
                path.append(inferred)

    dedup = []
    for p in path:
        if not dedup or dedup[-1] != p:
            dedup.append(p)
    return dedup

def evaluate_navigation_correctness(us_id_value: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    ref = find_nav_reference(us_id_value)
    if not ref:
        return {
            "correctness_pct": None,
            "correct_count": None,
            "evaluated_count": None,
            "details": [],
            "note": f"No navigation reference found for {us_id_value}"
        }

    expected_navigation = ref.get("expected_navigation", []) or []
    if not expected_navigation:
        return {
            "correctness_pct": None,
            "correct_count": None,
            "evaluated_count": None,
            "details": [],
            "note": f"No expected_navigation found for {us_id_value}"
        }

    evaluated_cases = 0
    correct_cases = 0
    details = []

    for tc in cases:
        actual = extract_actual_nav_path(tc)
        can_evaluate = len(actual) > 0
        is_correct = False

        if can_evaluate:
            evaluated_cases += 1

            min_len = min(len(actual), len(expected_navigation))
            is_correct = actual[:min_len] == expected_navigation[:min_len]

            if is_correct:
                correct_cases += 1

        details.append({
            "tc_id": tc.get("id", ""),
            "actual": actual,
            "expected": expected_navigation,
            "can_evaluate": can_evaluate,
            "is_correct": is_correct
        })

    correctness_pct = round((correct_cases / evaluated_cases) * 100, 2) if evaluated_cases else None

    return {
        "correctness_pct": correctness_pct,
        "correct_count": correct_cases,
        "evaluated_count": evaluated_cases,
        "details": details,
        "note": None if evaluated_cases else "No actual navigation could be extracted from generated test cases."
    }

def extract_required_roles(story: str, ac_blob: str) -> List[str]:
    text = normalize_text(story + " " + ac_blob)
    found = [r for r in ROLE_WORDS if r in text]
    return sorted(list(set(found)))

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

def evaluate_all(us_id_value: str, story: str, ac_blob: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "ac": evaluate_ac_coverage(us_id_value, cases),
        "navigation": evaluate_navigation_correctness(us_id_value, cases),
        "role": evaluate_role_coverage(story, ac_blob, cases)
    }

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

# ======================= BUTTONS =======================
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
    clicked_eval = st.button(
        "evaluate current output 📊",
        disabled=not bool(st.session_state.last_cases)
    )

st.markdown('</div>', unsafe_allow_html=True)

if clicked_without or clicked_with:
    use_ui = clicked_with

    with st.spinner("Generating test cases and building PDF..."):
        cases, open_q = generate_cases(user_story, ac_text, use_ui_context=use_ui)
        pdf_bytes = build_pdf(user_story, ac_text, cases, open_q, evaluation=None, us_id_value=us_id)

        st.session_state.last_pdf = pdf_bytes
        st.session_state.last_open_questions = open_q
        st.session_state.last_cases_count = len(cases)
        st.session_state.last_variant = "with_json" if use_ui else "without_json"
        st.session_state.last_cases = cases
        st.session_state.last_evaluation = None

if clicked_eval and st.session_state.last_cases:
    evaluation = evaluate_all(us_id, user_story, ac_text, st.session_state.last_cases)
    st.session_state.last_evaluation = evaluation
    st.session_state.last_pdf = build_pdf(
        user_story,
        ac_text,
        st.session_state.last_cases,
        st.session_state.last_open_questions,
        evaluation=evaluation,
        us_id_value=us_id
    )

# ======================= OUTPUT =======================
if st.session_state.last_variant:
    st.info(f"Generated with: {st.session_state.last_variant}")

if st.session_state.last_open_questions:
    cleaned_open_questions = _clean_open_questions(st.session_state.last_open_questions)
    st.warning("Notes / Open Questions:\n- " + "\n- ".join(cleaned_open_questions))

if st.session_state.last_evaluation:
    ev = st.session_state.last_evaluation

    st.subheader("Automated Evaluation")

    ac_metric = "N/A" if ev["ac"]["overall_pct"] is None else f"{ev['ac']['overall_pct']}%"
    nav_corr_metric = "N/A" if ev["navigation"]["correctness_pct"] is None else f"{ev['navigation']['correctness_pct']}%"
    role_metric = "N/A" if ev["role"]["overall_pct"] is None else f"{ev['role']['overall_pct']}%"

    m1, m2, m3 = st.columns(3)
    m1.metric("AC Coverage", ac_metric)
    m2.metric("Navigation Correctness", nav_corr_metric)
    m3.metric("Role Coverage", role_metric)

    if ev["ac"]["note"]:
        st.warning(ev["ac"]["note"])
    else:
        st.write(f"**AC Coverage:** {ev['ac']['covered_count']}/{ev['ac']['total_count']} ACs mit Score ≥ 0.8")
        with st.expander("AC details"):
            for d in ev["ac"]["details"]:
                st.write(f"{d['ac_id']}: score={d['score']} ({d['matched']}/{d['total_keywords']}) keywords={d['keywords']}")

    if ev["navigation"]["note"]:
        st.warning(ev["navigation"]["note"])
    else:
        st.write(f"**Navigation Correctness:** {ev['navigation']['correct_count']}/{ev['navigation']['evaluated_count']}")
        with st.expander("Navigation details"):
            for d in ev["navigation"]["details"]:
                st.write(
                    f"{d['tc_id']}: can_evaluate={d['can_evaluate']} "
                    f"correct={d['is_correct']} actual={d['actual']} "
                    f"expected={d['expected']}"
                )

    st.write(f"**Role Coverage:** {ev['role']['covered_count']}/{ev['role']['total_count']}")
    st.write(f"Required roles: {ev['role']['required_roles']}")
    st.write(f"Generated roles: {ev['role']['generated_roles']}")
    if ev["role"]["missing_roles"]:
        st.warning(f"Missing roles: {ev['role']['missing_roles']}")

if st.session_state.last_pdf:
    st.success(f"PDF ready ✅ (test cases: {st.session_state.last_cases_count})")
    st.download_button(
        "download PDF 🧾",
        data=st.session_state.last_pdf,
        file_name=f"test_design_{us_id}_{st.session_state.last_variant or 'result'}.pdf",
        mime="application/pdf",
    )
