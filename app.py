# app.py — UI unchanged (Aqua + Comic Sans + Password Gate) + ui_context + spinner + persistent download
# Run:
#   pip install streamlit python-dotenv reportlab openai
#   streamlit run app.py

import os
import io
import json
import re

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

# --- OpenAI ---
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

# ======================= GLOBAL FONT (Comic Sans everywhere) =======================
st.markdown("""
<style>
:root { --comic: "Comic Sans MS","Comic Sans",cursive; }

/* Hit all major Streamlit containers + common widgets */
html, body, .stApp, .stAppViewContainer, .main, .block-container,
.stMarkdown, .stAlert, .stDataFrame, .stForm,
.stTextInput, .stTextArea, .stSelectbox, .stMultiSelect, .stNumberInput,
.stButton > button, .stDownloadButton > button,
label, p, span, div {
  font-family: var(--comic) !important;
}
</style>
""", unsafe_allow_html=True)

# ======================= PASSWORD GATE (same vibe) =======================
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

# ======================= MAIN UI (keep original look) =======================
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

.stTextArea textarea {
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

# ======================= UI CONTEXT LOADER =======================
UI_CONTEXT_PATH = "ui_context.json"

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
        st.error(f"UI context could not be loaded: {e}")
        return {}

UI_CONTEXT = load_ui_context(UI_CONTEXT_PATH)
st.caption(f"UI context loaded nodes: {len(UI_CONTEXT.get('nodes', []))}")

# ======================= OPENAI SETUP =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

SYSTEM_PROMPT = """
You are a senior test engineer.
Return ONLY valid JSON (no markdown, no prose).

You may receive a UI structure as 'ui_context' (JSON with nodes and relationships).
If ui_context is provided, you MUST use it to generate concrete navigation.

STRICT UI RULES (MANDATORY):
- Do NOT invent menus/screens/buttons/fields that are not present in ui_context.nodes.
- Every step MUST include 'ui_node_id' that matches an existing ui_context.nodes[].id.
- Navigation must be explicit and beginner-friendly (click path through menus/screens).
- Generic steps like "Navigate to X" are NOT allowed if ui_context provides the path elements.

ACCEPTANCE CRITERIA COVERAGE IS MANDATORY:
- Create 1–2 test cases per acceptance criterion (group only if it is natural).
- Every acceptance criterion MUST be mapped to at least one test case.

CRITICAL: VERBATIM REQUIREMENTS HANDLING
- You MUST copy every acceptance criterion line EXACTLY (verbatim) into the output under "requirements".
- You MUST NOT paraphrase requirements text.
- Each test case MUST list which requirement IDs it covers.
- Each test step MUST include a "derived_from" array referencing the requirement IDs that justify the step.
- If a requirement mentions UI control behavior (e.g., multiselect, disabled, becomes active), the test steps MUST explicitly test that behavior (not just the field presence).
- If you cannot incorporate a word/detail from a requirement, add an open_questions entry referencing that requirement ID and explain what is missing in ui_context.

NAVIGATION IS MANDATORY AND MUST BE EXPLICIT:
- For EVERY test case, the first navigation steps MUST start from a Console node (type="console"),
  then click the corresponding nav_option, then reach the target screen.
- You MUST express navigation using the ui_context parent chain.
- Generic navigation phrases are NOT allowed (e.g., "Navigate to MAP Dashboard" is forbidden).
- Each navigation step MUST reference a concrete ui_node_id.

EXAMPLE FORMAT (must follow this style):
1) Open "OAM Console" (CONSOLE-OAM)
2) Select "MAP Review" (OAM-OPT-MAP-REVIEW)
3) Verify "MAP Dashboard" is displayed (SCR-MAP-DASHBOARD)



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

RULES:
- Provide focused test cases.
- Each test case must contain navigation_steps (if ui_context is provided).
- Each test case MUST have at least 3 steps total (navigation_steps + steps).
- Ensure acceptance criteria are covered across the set.
- Test cases are divided by menu, not by functionality. So for example you test several fields and their functionality in one test case
- Be concise and testable. No Gherkin.
"""

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

def generate_cases(story: str, ac_blob: str):
    if not client:
        return [], ["OpenAI client not initialized (missing OPENAI_API_KEY or openai package)."]
    if not story.strip():
        return [], ["User story is empty."]

    payload = {
        "story": story.strip(),
        "acceptance_criteria": [l.strip() for l in ac_blob.splitlines() if l.strip()],
        "ui_context": UI_CONTEXT,
    }

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        data = _json_from_text(resp.choices[0].message.content)

        tcs = data.get("test_cases", []) or []
        open_q = data.get("open_questions", []) or []

        fixed = []
        for tc in tcs:
            nav = [_normalize_step(s) for s in (tc.get("navigation_steps", []) or [])]
            steps = [_normalize_step(s) for s in (tc.get("steps", []) or [])]

            # Merge nav into main steps so PDF always shows the navigation
            merged_steps = nav + steps

            while len(merged_steps) < 3:
                merged_steps.append({"step": "—", "expected": "—", "ui_node_id": None})

            fixed.append(
                {
                    "id": (tc.get("id", "") or "").strip(),
                    "title": (tc.get("title", "") or "").strip(),
                    "priority": (tc.get("priority", "") or "").strip(),
                    "type": (tc.get("type", "") or "").strip(),
                    "steps": merged_steps,
                }
            )

        return fixed, open_q
    except Exception as e:
        return [], [f"OpenAI call failed: {e}"]

# ======================= PDF BUILDER =======================
def build_pdf(story_text: str, ac_blob: str, cases: list, open_questions: list) -> bytes:
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

    if open_questions:
        flow.append(Paragraph("<b>Open Questions</b>", head))
        flow.append(
            ListFlowable(
                [ListItem(Paragraph(q, body), leftIndent=6) for q in open_questions],
                bulletType="bullet",
                leftPadding=12,
            )
        )
        flow.append(Spacer(1, 12))

    if cases:
        flow.append(Paragraph("<b>Generated Test Design</b>", head))
        flow.append(Spacer(1, 6))

        # Summary table
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

        # One table per test case
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

# ======================= EXPORT (spinner + persistent download) =======================
if "last_pdf" not in st.session_state:
    st.session_state.last_pdf = None
if "last_open_questions" not in st.session_state:
    st.session_state.last_open_questions = []
if "last_cases_count" not in st.session_state:
    st.session_state.last_cases_count = 0

st.markdown('<div class="export-wrap">', unsafe_allow_html=True)
clicked = st.button(
    "export test cases ✨",
    disabled=not (user_story.strip() and ac_text.strip())
)
st.markdown('</div>', unsafe_allow_html=True)

if clicked:
    with st.spinner("Generating test cases and building PDF..."):
        cases, open_q = generate_cases(user_story, ac_text)
        pdf_bytes = build_pdf(user_story, ac_text, cases, open_q)

        st.session_state.last_pdf = pdf_bytes
        st.session_state.last_open_questions = open_q
        st.session_state.last_cases_count = len(cases)

if st.session_state.last_open_questions:
    st.warning("Notes / Open Questions:\n- " + "\n- ".join(st.session_state.last_open_questions))

if st.session_state.last_pdf:
    st.success(f"PDF ready ✅ (test cases: {st.session_state.last_cases_count})")
    st.download_button(
        "download PDF 🧾",
        data=st.session_state.last_pdf,
        file_name="test_design.pdf",
        mime="application/pdf",
    )



