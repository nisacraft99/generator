# app.py
# Run:
#   conda activate thesis
#   pip install streamlit python-dotenv reportlab openai
#   streamlit run app.py

import os, io, json, re
import streamlit as st
from dotenv import load_dotenv
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
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
html, body, .stApp, .main, .block-container,
.stMarkdown, .stTextInput, .stTextArea, .stButton > button {
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
    else:
        st.error("Wrong password 🫠")

if not st.session_state.auth_ok:
    st.markdown("""
    <div style='max-width:600px;margin:10vh auto;text-align:center;'>
      <h1 style='background:#f8c9ea;padding:15px;border-radius:15px;'>User Story to Testcase Generator</h1>
      <p>🔒 private app – enter password</p>
    </div>
    """, unsafe_allow_html=True)
    st.text_input("Password", type="password", key="pw_input", label_visibility="collapsed")
    st.button("let me in ✨", on_click=try_login)
    st.stop()

# ======================= MAIN UI =======================
st.markdown("<h1 style='text-align:center;'>User Story → Testcase Generator</h1>", unsafe_allow_html=True)

st.markdown("### enter your user story")
user_story = st.text_area("", height=120, placeholder="As a user I want ...")

st.markdown("### enter acceptance criteria (1 per line)")
ac_text = st.text_area("", height=200)

# ======================= LOAD UI CONTEXT =======================
UI_CONTEXT_PATH = "ui_context.json"

def load_ui_context(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            ctx = json.load(f)
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
Return ONLY valid JSON.

If ui_context is provided:
- You MUST use it.
- Every step MUST include ui_node_id from ui_context.nodes[].id.
- Navigation must be explicit and beginner-friendly.
- Do NOT invent UI elements.

Schema:
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

def _json_from_text(txt: str):
    try:
        return json.loads(txt)
    except:
        return {"test_cases": [], "open_questions": ["Invalid JSON from model"]}

def generate_cases(story: str, ac_blob: str):
    if not client:
        return [], ["OpenAI client not initialized"]

    payload = {
        "story": story.strip(),
        "acceptance_criteria": [l.strip() for l in ac_blob.splitlines() if l.strip()],
        "ui_context": UI_CONTEXT
    }

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload)}
            ]
        )

        data = _json_from_text(resp.choices[0].message.content)
        tcs = data.get("test_cases", [])
        open_q = data.get("open_questions", [])

        fixed = []
        for tc in tcs:
            nav = tc.get("navigation_steps", []) or []
            steps = tc.get("steps", []) or []
            merged = nav + steps

            while len(merged) < 3:
                merged.append({"step": "—", "expected": "—", "ui_node_id": None})

            fixed.append({
                "id": tc.get("id",""),
                "title": tc.get("title",""),
                "priority": tc.get("priority",""),
                "type": tc.get("type",""),
                "steps": merged
            })

        return fixed, open_q

    except Exception as e:
        return [], [f"OpenAI call failed: {e}"]

# ======================= PDF BUILDER =======================
def build_pdf(story, ac_blob, cases, open_q):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()

    flow = []
    flow.append(Paragraph("<b>User Story</b>", styles["Heading2"]))
    flow.append(Paragraph(story, styles["Normal"]))
    flow.append(Spacer(1,10))

    flow.append(Paragraph("<b>Acceptance Criteria</b>", styles["Heading2"]))
    for line in ac_blob.splitlines():
        if line.strip():
            flow.append(Paragraph("• " + line.strip(), styles["Normal"]))
    flow.append(Spacer(1,10))

    if open_q:
        flow.append(Paragraph("<b>Open Questions</b>", styles["Heading2"]))
        for q in open_q:
            flow.append(Paragraph("• " + q, styles["Normal"]))
        flow.append(Spacer(1,10))

    for tc in cases:
        flow.append(Paragraph(f"<b>{tc['id']} — {tc['title']}</b>", styles["Heading3"]))
        table_data = [["Step", "Action", "Expected Result"]]

        for i, s in enumerate(tc["steps"], start=1):
            table_data.append([str(i), s["step"], s["expected"]])

        table = Table(table_data, colWidths=[40,250,250])
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.lightblue),
            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ]))

        flow.append(table)
        flow.append(Spacer(1,15))

    doc.build(flow)
    return buf.getvalue()

# ======================= EXPORT BUTTON =======================
if "last_pdf" not in st.session_state:
    st.session_state.last_pdf = None
if "last_open_questions" not in st.session_state:
    st.session_state.last_open_questions = []
if "last_cases_count" not in st.session_state:
    st.session_state.last_cases_count = 0

clicked = st.button("export test cases ✨", disabled=not (user_story.strip() and ac_text.strip()))

if clicked:
    with st.spinner("Generating test cases and building PDF..."):
        cases, open_q = generate_cases(user_story, ac_text)
        pdf_bytes = build_pdf(user_story, ac_text, cases, open_q)

        st.session_state.last_pdf = pdf_bytes
        st.session_state.last_open_questions = open_q
        st.session_state.last_cases_count = len(cases)

if st.session_state.last_open_questions:
    st.warning("Notes:\n- " + "\n- ".join(st.session_state.last_open_questions))

if st.session_state.last_pdf:
    st.success(f"PDF ready ✅ (test cases: {st.session_state.last_cases_count})")
    st.download_button(
        "download PDF 🧾",
        data=st.session_state.last_pdf,
        file_name="test_design.pdf",
        mime="application/pdf"
    )
